import os
import time
import io
import base64
import re
from datetime import datetime

import numpy as np
from PIL import Image, ImageDraw
from flask import Flask, request, render_template, jsonify, send_file


# =========================================================
# OPTIONAL: Firebase Initialization (safe for public repos)
# =========================================================
db = None
try:
    key_path = os.getenv("FIREBASE_KEY")  # must be set manually by the user

    if key_path:
        import firebase_admin
        from firebase_admin import credentials, firestore

        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase initialized.")
    else:
        print("Firebase disabled (no FIREBASE_KEY environment variable).")

except Exception:
    print("Firebase initialization skipped.")
    db = None


# =========================================================
# Device Config
# =========================================================
PORT_NAME    = "COM7"
BAUDRATE     = 115200
READ_TIMEOUT = 3.0
TOTAL_WAIT   = 6.0

W, H = 160, 160
ROI_SIZE = 50
N = W * H

# Viral cutoffs
CUTOFF_HIV = 97.5
CUTOFF_HBV = 195.5
CUTOFF_HCV = 134.7

# Default ROI centers
DEFAULT_ROIS = [
    {"cx": 35,  "cy": 125},  # Internal Control
    {"cx": 125, "cy": 125},  # HIV
    {"cx": 35,  "cy": 35},   # HBV
    {"cx": 125, "cy": 35},   # HCV
]

app = Flask(__name__, static_folder="static", template_folder="templates")

# Last captured or loaded frame
last_frame = None


# ======================================================
# Utility — numpy array → PNG base64
# ======================================================
def numpy_to_png_base64(arr, scale=3):
    img = Image.fromarray(arr, mode="L")
    img = img.resize((arr.shape[1] * scale, arr.shape[0] * scale), Image.NEAREST)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ======================================================
# Utility — ROI overlay image (base64)
# ======================================================
def generate_overlay_image(arr, rois, scale=3):
    img = Image.fromarray(arr, mode="L")
    img = img.resize((arr.shape[1] * scale, arr.shape[0] * scale), Image.NEAREST)
    img = img.convert("RGB")

    draw = ImageDraw.Draw(img)

    colors = [
        (0, 163, 255),   # Internal
        (255, 107, 107), # HIV
        (255, 217, 61),  # HBV
        (124, 255, 145)  # HCV
    ]
    names = ["Internal", "HIV", "HBV", "HCV"]

    for i, r in enumerate(rois):
        cx, cy = r["cx"], r["cy"]
        half = ROI_SIZE // 2

        x1 = (cx - half) * scale
        y1 = (cy - half) * scale
        x2 = (cx + half) * scale
        y2 = (cy + half) * scale

        draw.rectangle([x1, y1, x2, y2], outline=colors[i], width=3)
        draw.text((x1 + 5, y1 + 5), f"{names[i]} ({cx},{cy})", fill=colors[i])

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ======================================================
# Read pixels from MCU via Serial
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
# ROI Helpers
# ======================================================
def clamp_centroid(cx, cy):
    half = ROI_SIZE // 2
    cx = int(max(half, min(W - half, cx)))
    cy = int(max(half, min(H - half, cy)))
    return cx, cy


def centroid_to_xy(cx, cy):
    half = ROI_SIZE // 2
    return int(cx - half), int(cy - half)


# ======================================================
# Routes
# ======================================================
@app.route("/")
def index():
    return render_template("index.html", default_rois=DEFAULT_ROIS)


# ------------------------- Capture -------------------------
@app.route("/api/capture", methods=["POST"])
def capture():
    global last_frame
    try:
        frame = read_pixels_from_serial()
    except Exception:
        frame = (np.random.rand(H, W) * 255).astype(np.uint8)

    rotated = np.rot90(frame, k=-1)
    last_frame = rotated

    return jsonify({
        "ok": True,
        "image_b64": numpy_to_png_base64(rotated, scale=3)
    })


# ------------------------- Load CSV -------------------------
@app.route("/api/open_csv", methods=["POST"])
def open_csv():
    global last_frame

    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file uploaded"}), 400

    file = request.files["file"]

    try:
        data = np.loadtxt(file, delimiter=",", dtype=np.uint8).flatten()

        if data.size != N:
            return jsonify({"ok": False, "error": f"CSV has {data.size} values, expected {N}"}), 400

        frame = data.reshape((H, W))
        rotated = np.rot90(frame, k=-1)
        last_frame = rotated

        return jsonify({"ok": True, "image_b64": numpy_to_png_base64(rotated)})
    except Exception as e:
        return jsonify({"ok": False, "error": f"CSV parse error: {e}"}), 400


# ------------------------- Extract -------------------------
@app.route("/api/extract", methods=["POST"])
def extract():
    global last_frame

    if last_frame is None:
        return jsonify({"ok": False, "error": "Capture or Open CSV first"})

    rois = request.get_json().get("rois", [])
    if len(rois) != 4:
        return jsonify({"ok": False, "error": "Need 4 ROIs"})

    coords = []
    for r in rois:
        cx, cy = clamp_centroid(r["cx"], r["cy"])
        coords.append(centroid_to_xy(cx, cy))

    arr = last_frame.copy()
    vals = [arr[y:y + ROI_SIZE, x:x + ROI_SIZE].reshape(-1) for x, y in coords]
    all_vals = np.concatenate(vals)

    vmin, vmax = int(all_vals.min()), int(all_vals.max())
    if vmax > vmin:
        norm = np.rint((all_vals - vmin) * (255 / (vmax - vmin))).astype(np.uint8)
    else:
        norm = np.zeros_like(all_vals)

    roi1, roi2, roi3, roi4 = [norm[i * 2500:(i + 1) * 2500] for i in range(4)]

    def score(r):
        return float((r.astype(np.float64) / 255.0).sum())

    ic_ok = not np.all(roi1 == 0)

    hiv_score = score(roi2)
    hbv_score = score(roi3)
    hcv_score = score(roi4)

    hiv_status = "Positive" if hiv_score > CUTOFF_HIV else "Negative"
    hbv_status = "Positive" if hbv_score > CUTOFF_HBV else "Negative"
    hcv_status = "Positive" if hcv_score > CUTOFF_HCV else "Negative"

    # --- Save CSV ---
    now = datetime.now()
    dirpath = f"roi_extract/{now:%m-%d-%Y}"
    os.makedirs(dirpath, exist_ok=True)
    csv_path = f"{dirpath}/{now:%H-%M-%S}_ROI.csv"
    np.savetxt(csv_path, norm[None, :], fmt="%d", delimiter=",")

    # --- ROI Overlay ---
    overlay_b64 = generate_overlay_image(last_frame, rois)

    # --- Firebase Upload (only if configured) ---
    if db is not None:
        try:
            db.collection("results").document("latest").set({
                "timestamp": now.isoformat(),

                "image_b64": overlay_b64,
                "ic_ok": bool(ic_ok),

                "hiv_status": hiv_status,
                "hbv_status": hbv_status,
                "hcv_status": hcv_status,

                "hiv_score": hiv_score,
                "hbv_score": hbv_score,
                "hcv_score": hcv_score,
            })
        except Exception:
            pass

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


# ------------------------- Download CSV -------------------------
@app.route("/download/<path:filename>")
def download(filename):
    if not filename.startswith("roi_extract"):
        return "Invalid path", 400
    return send_file(filename, as_attachment=True)


# ======================================================
# Entry
# ======================================================
if __name__ == "__main__":
    print("Server running at: http://127.0.0.1:5050")
    app.run(host="127.0.0.1", port=5050, debug=False)
