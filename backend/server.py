import os
import time
import io
import base64
import re
from datetime import datetime

import numpy as np
from PIL import Image
from flask import Flask, request, render_template, jsonify, send_file

# Firebase (optional)
USE_FIREBASE = False
if os.getenv("FIREBASE_KEY"):
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        cred = credentials.Certificate(os.getenv("FIREBASE_KEY"))
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        USE_FIREBASE = True
        print("Firebase initialized.")
    except Exception as e:
        print("Firebase disabled:", e)
        USE_FIREBASE = False

# -------------------
# Config
# -------------------
PORT_NAME    = "COM7"      # 사용자 환경에 따라 변경
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

last_frame = None


# -----------------------
# Utility
# -----------------------
def numpy_to_png_base64(arr, scale=3):
    img = Image.fromarray(arr, mode="L")
    img = img.resize((arr.shape[1]*scale, arr.shape[0]*scale), Image.NEAREST)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# -----------------------
# MCU pixel read
# -----------------------
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


def clamp_centroid(cx, cy):
    half = ROI_SIZE // 2
    cx = int(max(half, min(W-half, cx)))
    cy = int(max(half, min(H-half, cy)))
    return cx, cy


def centroid_to_xy(cx, cy):
    half = ROI_SIZE // 2
    return int(cx - half), int(cy - half)


# -------------------------
# Routes
# -------------------------
@app.route("/")
def index():
    return render_template("index.html", default_rois=DEFAULT_ROIS)


@app.route("/api/capture", methods=["POST"])
def capture():
    global last_frame
    try:
        frame = read_pixels_from_serial()
    except Exception:
        frame = (np.random.rand(H, W)*255).astype(np.uint8)

    rotated = np.rot90(frame, k=-1)
    last_frame = rotated

    return jsonify({
        "ok": True,
        "image_b64": numpy_to_png_base64(rotated, scale=3)
    })


@app.route("/api/extract", methods=["POST"])
def extract():
    global last_frame
    if last_frame is None:
        return jsonify({"ok": False, "error": "Capture first"})

    payload = request.get_json()
    rois = payload.get("rois", [])

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

    score = lambda r: float((r/255).sum())

    ic_ok = not np.all(roi1 == 0)
    hiv_score = score(roi2)
    hbv_score = score(roi3)
    hcv_score = score(roi4)

    hiv_status = "Positive" if hiv_score > CUTOFF_HIV else "Negative"
    hbv_status = "Positive" if hbv_score > CUTOFF_HBV else "Negative"
    hcv_status = "Positive" if hcv_score > CUTOFF_HCV else "Negative"

    now = datetime.now()
    dirpath = f"roi_extract/{now:%m-%d-%Y}"
    os.makedirs(dirpath, exist_ok=True)
    csv_path = f"{dirpath}/{now:%H-%M-%S}_ROI.csv"

    np.savetxt(csv_path, norm[None, :], fmt="%d", delimiter=",")

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


@app.route("/download/<path:filename>")
def download(filename):
    if not filename.startswith("roi_extract"):
        return "Invalid path", 400
    return send_file(filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)

