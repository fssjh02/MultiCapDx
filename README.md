# Multicap Dx Web UI

This repository contains the **web-based user interface and backend engine** for the Multicap Dx platform, which performs bubble-induced 3D capacitance profiling for quantitative multi-viral antigen detection (HIV, HBV, HCV).

The goal of this repo is that **anyone with a clean computer (only Python installed)** can reproduce the core results of the web-based Multicap Dx workflow using:

- MCU + sensor board (to stream 160×160 grayscale frames)
- Python/Flask backend (data acquisition & analysis)
- Web UI (ROI control & result display)

---

## 1. Repository structure

```text
MulticapDx/
│
├── backend/               # Python Flask server (engine)
│   ├── server.py          # Main Flask app (capture + extract)
│   ├── requirements.txt   # Python dependencies
│   ├── static/            # CSS, JS, logo
│   │   ├── style.css
│   │   ├── app.js
│   │   └── lab_logo.png   # (optional)
│   └── templates/
│       └── index.html     # Web UI template (Flask)
│
├── mcufirmware/           # MCU firmware (example)
│   ├── multicapdx_sensor.ino
│   └── README_mcu.md
│
├── sample_data/           # Optional example CSV files
│   ├── example_negative.csv
│   └── example_positive.csv
│
├── docs/                  # Figures, diagrams, screenshots (optional)
│   └── system_diagram.png
│
└── README.md

```

2. Components and Roles (Beginner-Friendly)
2.1 MCU + Sensor Board

Reads capacitance-based bubble height signals from the Multicap Dx sensor

Streams a 160×160 grayscale frame (0–255) via USB serial

Functions like a low-resolution “camera” for bubble profiles

The example firmware (mcufirmware/multicapdx_sensor.ino) demonstrates how to respond to a 99\n command by outputting 25,600 comma-separated pixel values

2.2 Python/Flask Backend (backend/server.py)

The backend provides the full analysis pipeline:

Sends 99\n to the MCU to trigger frame acquisition

Receives a 160×160 frame from the MCU

Converts the frame into a PNG image for display

Applies four ROIs (Internal, HIV, HBV, HCV)

Performs per-frame min–max normalization inside ROIs

Computes viral scores (sum of normalized values)

Generates Positive/Negative decisions

Saves normalized ROI values into a CSV file

Exposes REST endpoints:

Endpoint	Function
POST /api/capture	Acquire and return a new frame
POST /api/extract	Perform ROI extraction and scoring
GET /download/...	Download normalized ROI CSV
2.3 Web UI (HTML/CSS/JS)

The browser interface (index.html + style.css + app.js):

Displays the sensor frame with color-coded ROI boxes

Allows pixel-level adjustment of each ROI

Provides RUN and Extract & Analyze buttons

Shows Internal control status and viral Positive/Negative calls

Lets the user download normalized ROI data as a CSV

Runs entirely in the browser—no installation required.

2.4 Firebase (Optional)

Some deployments connect to Firebase Firestore for remote result monitoring.
Firebase is not required for reproducing the analysis pipeline.
Service account keys are intentionally not included for security.

To enable Firebase (optional):
```
export FIREBASE_KEY=/path/to/your/firebase_key.json
```
3. How to Run (From a Clean Machine)
3.1 Install Python dependencies
```
cd backend
pip install -r requirements.txt
```

3.2 Connect the MCU

Upload the example firmware or your own firmware that outputs a 160×160 frame

Edit PORT_NAME in server.py to match your system

Windows example: "COM7"

Linux/Mac example: "/dev/ttyACM0"

3.3 Run the Flask backend
```
python server.py
```

Expected output:
```
Running on http://127.0.0.1:5050
```
3.4 Open the Web UI

Open any browser (Chrome/Edge):

➡ http://127.0.0.1:5050

Then:

RUN — captures a frame

Adjust ROIs if necessary

Extract & Analyze — calculates viral scores

Download CSV — saves normalized ROI data

4. Reproducibility Notes

ROI normalization and scoring follow the exact method used in the primary experiments

No filtering or temporal smoothing is applied

CSV files contain the exact normalized ROI values used in scoring

Example CSV files (positive/negative) are included in sample_data/

5. Citation

If this code is used in a scientific publication, please cite:

Multicap Dx Web UI & Backend
Source code available at: https://github.com/fssjh02/MultiCapDx


