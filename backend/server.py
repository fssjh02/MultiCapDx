import os
import time
import io
import base64
import re
from datetime import datetime

import numpy as np
from PIL import Image, ImageDraw
from flask import Flask, request, render_template, jsonify, send_file


# =========================
# Firebase 초기화
# =========================
db = None
try:
    key_path = os.getenv("FIREBASE_KEY")
    if not key_path:
        key_path = r"c:/Users/User/Desktop/bubble/Bubble 2/file/UI code/multicapdx-firebase-admin.json"

    import firebase_admin
    from firebase_admin import credentials, firestore

    cred = credentials.Certificate(key_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase initialized:", key_path)

except Exception as e:
    print("⚠️ Firebase init failed:", e)
    db = None


# -------------------
# Config
# -------------------
PORT_NAME    = "COM7"
BAUDRATE     = 115200
READ_TIMEOUT = 3.0
TOTAL_WAIT   = 6.0

W, H = 160, 160
ROI_SIZE = 50
N = W * H

# Cutoffs
CUTOFF_HIV = 97.5
CUTOFF_HBV = 195.5
CUTOFF_HCV = 134.7

# Default ROIs
DEFAULT_ROIS = [
    {"cx": 35,  "cy": 125},  # Internal
    {"cx": 125, "cy": 125},  # HIV
    {"cx": 35,  "cy": 35},   # HBV
    {"cx": 125, "cy": 35},   # HCV
]

app = Flask(__name__, static_folder="static", template_folder="templates")

# 최근 프레임 (디바이스 캡쳐 or CSV 로드)
last_frame = None


# ======================================================
# Utility — RAW → PNG base64
# ======================================================
def numpy_to_png_base64(arr, scale=3):
    img = Image.fromarray(arr, mode="L")
    img = img.resize((arr.shape[1]*scale, arr.shape[0]*scale), Image.NEAREST)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ======================================================
# Utility — ROI Overlay 이미지 생성 (PNG base64)
# ======================================================
def generate_overlay_image(arr, rois, scale=3):
    """ROI가 그려진 overlay PNG(base64)를 생성"""
    img = Image.fromarray(arr, mode="L")
    img = img.resize((arr.shape[1]*scale, arr.shape[0]*scale), Image.NEAREST)
    img = img.convert("RGB")

    draw = ImageDraw.Draw(img)

    colors = [
        (0, 163, 255),   # Internal (blue)
        (255, 107, 107), # HIV (red)
        (255, 217, 61),  # HBV (yellow)
        (124, 255, 145)  # HCV (green)
    ]
    names = ["Internal", "HIV", "HBV", "HCV"]

    for i, r in enumerate(rois):
        cx, cy = r["cx"], r["cy"]
        half = ROI_SIZE // 2

        x1 = (cx - half) * scale
        y1 = (cy - half) * scale
        x2 = (cx + half) * scale
        y2 = (cy + half) * scale

        # ROI rectangle
        draw.rectangle([x1, y1, x2, y2], outline=colors[i], width=3)

        # Label
        draw.text((x1 + 5, y1 + 5), f"{names[i]} ({cx},{cy})", fill=colors[i])

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ======================================================
# MCU pixel read
# ======================================================
def read_pixels_from_serial():
    import serial
    with serial.Serial(PORT_NAME, baudrate=BAUDRATE, timeout=READ_TIMEOUT) as mcu:
        mcu.write(b"99\n")

        tokens = []
        buf = b""
        start = time.time()

        while len(tokens) < N:
            chunk = mcu.read(4096)
            if not chunk:
                if time.time() - start > TOTAL_WAIT:
                    break
                continue

            buf += chunk
            text = buf.decode("utf-8", errors="ignore")
            parts = re.split(r"[,\s]+", text.strip())
            tail = ""

            if parts and not text.endswith((",", " ", "\n", "\r", "\t")):
                tail = parts.pop()

            for p in parts:
                if p.isdigit():
                    tokens.append(int(p))

            buf = tail.encode("utf-8")

        if len(tokens) < N:
            raise RuntimeError("MCU sent too few pixels")

        return np.array(tokens, dtype=np.uint8).reshape((H, W))


# ======================================================
# ROI coordinate utils
# ======================================================
def clamp_centroid(cx, cy):
    half = ROI_SIZE // 2
    cx = int(max(half, min(W-half, cx)))
    cy = int(max(half, min(H-half, cy)))
    return cx, cy


def centroid_to_xy(cx, cy):
    half = ROI_SIZE // 2
    return int(cx - half), int(cy - half)


# ======================================================
# Routes
# ======================================================
@app.route("/")
def index():
    print("🔥 Loading index.html from:", os.path.abspath("templates/index.html"))
    return render_template("index.html", default_rois=DEFAULT_ROIS)


# ------------------------- Capture (디바이스) -------------------------
@app.route("/api/capture", methods=["POST"])
def capture():
    global last_frame
    try:
        frame = read_pixels_from_serial()
    except Exception as e:
        print("[Serial error → random frame]:", e)
        frame = (np.random.rand(H, W)*255).astype(np.uint8)

    # 디바이스에서 읽은 프레임을 회전 후 last_frame에 저장
    rotated = np.rot90(frame, k=-1)
    last_frame = rotated

    return jsonify({
        "ok": True,
        "image_b64": numpy_to_png_base64(rotated, scale=3)
    })


# ------------------------- Open CSV (로컬 파일에서 프레임 로드) -------------------------
@app.route("/api/open_csv", methods=["POST"])
def open_csv():
    global last_frame

    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"ok": False, "error": "Empty filename"}), 400

    try:
        # strictly read as integers (uint8 compatible)
        data = np.loadtxt(file, delimiter=",", dtype=np.uint8)
        flat = data.flatten()

        if flat.size != N:
            return jsonify({
                "ok": False,
                "error": f"CSV has {flat.size} values, expected {N} (160x160)."
            }), 400

        # reshape to frame
        frame = flat.reshape((H, W))

        # rotate same as device capture
        rotated = np.rot90(frame, k=-1)
        last_frame = rotated

        return jsonify({
            "ok": True,
            "image_b64": numpy_to_png_base64(rotated, scale=3)
        })

    except Exception as e:
        print("CSV parse error:", e)
        return jsonify({"ok": False, "error": f"CSV parse error: {e}"}), 400



# ------------------------- Extract + Firestore upload -------------------------
@app.route("/api/extract", methods=["POST"])
def extract():
    global last_frame
    if last_frame is None:
        return jsonify({"ok": False, "error": "Capture or Open CSV first"})

    payload = request.get_json() or {}
    rois = payload.get("rois", [])
    if len(rois) != 4:
        return jsonify({"ok": False, "error": "Need 4 ROIs"})

    coords = []
    for r in rois:
        cx, cy = clamp_centroid(r["cx"], r["cy"])
        coords.append(centroid_to_xy(cx, cy))

    arr = last_frame.copy()
    vals = [arr[y:y+ROI_SIZE, x:x+ROI_SIZE].reshape(-1) for x, y in coords]
    all_vals = np.concatenate(vals)

    vmin, vmax = int(all_vals.min()), int(all_vals.max())
    if vmax > vmin:
        norm = np.rint((all_vals - vmin) * (255/(vmax-vmin))).astype(np.uint8)
    else:
        norm = np.zeros_like(all_vals)

    roi1, roi2, roi3, roi4 = [norm[i*2500:(i+1)*2500] for i in range(4)]

    def score(r):
        return float((r.astype(np.float64)/255.0).sum())

    ic_ok = not np.all(roi1 == 0)
    hiv_score = score(roi2)
    hbv_score = score(roi3)
    hcv_score = score(roi4)

    hiv_status = "Positive" if hiv_score > CUTOFF_HIV else "Negative"
    hbv_status = "Positive" if hbv_score > CUTOFF_HBV else "Negative"
    hcv_status = "Positive" if hcv_score > CUTOFF_HCV else "Negative"

    # --- CSV 저장 ---
    now = datetime.now()
    dirpath = f"roi_extract/{now:%m-%d-%Y}"
    os.makedirs(dirpath, exist_ok=True)
    csv_path = f"{dirpath}/{now:%H-%M-%S}_ROI.csv"
    np.savetxt(csv_path, norm[None, :], fmt="%d", delimiter=",")

    # ==============================
    # 🔥 ROI Overlay PNG 생성
    # ==============================
    overlay_b64 = generate_overlay_image(last_frame, rois, scale=3)

    # ==============================
    # 🔥 Firestore 업로드
    # ==============================
    if db is not None:
        try:
            doc = {
                "timestamp": now.isoformat(),
                "image_b64": overlay_b64,  # ← ROI Overlay 포함됨
                "ic_ok": bool(ic_ok),

                "hiv_status": hiv_status,
                "hbv_status": hbv_status,
                "hcv_status": hcv_status,

                "hiv_score": float(hiv_score),
                "hbv_score": float(hbv_score),
                "hcv_score": float(hcv_score),

                "cutoff_hiv": float(CUTOFF_HIV),
                "cutoff_hbv": float(CUTOFF_HBV),
                "cutoff_hcv": float(CUTOFF_HCV),
            }
            db.collection("results").document("latest").set(doc)
            print("🔥 Firestore updated with ROI overlay image")
        except Exception as e:
            print("❌ Firestore upload error:", e)

    return jsonify({
        "ok": True,
        "csv": csv_path,
        "ic_ok": ic_ok,
        "hiv": {"status": hiv_status, "score": hiv_score},
        "hbv": {"status": hbv_status, "score": hbv_score},
        "hcv": {"status": hcv_status, "score": hcv_score},
        "vmin": vmin,
        "vmax": vmax
    })


# ------------------------- Download -------------------------
@app.route("/download/<path:filename>")
def download(filename):
    if not filename.startswith("roi_extract"):
        return "Invalid path", 400
    return send_file(filename, as_attachment=True)


if __name__ == "__main__":
    print("http://127.0.0.1:5050 running…")
    app.run(host="127.0.0.1", port=5050, debug=False)


print("TEMPLATE DIR =", app.template_folder)
