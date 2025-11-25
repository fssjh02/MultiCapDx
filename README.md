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


---

## 2. Components and Roles (Beginner-Friendly)

### 2.1 MCU + Sensor Board
- Reads capacitance-based bubble height signals from the Multicap Dx sensor  
- Streams a **160×160 grayscale frame (0–255)** via USB serial  
- Functions like a low-resolution “camera” for bubble profiles  
- The example firmware (`mcufirmware/multicapdx_sensor.ino`) demonstrates how to respond to a `99\n` command by outputting 25,600 comma-separated pixel values  

---

### 2.2 Python/Flask Backend (`backend/server.py`)
The backend provides the full analysis workflow:

1. Sends `99\n` to the MCU to trigger frame acquisition  
2. Receives a 160×160 frame from the MCU  
3. Converts the frame into a PNG image for the browser  
4. Applies four ROIs (Internal, HIV, HBV, HCV)  
5. Performs per-frame **min–max normalization** inside ROIs  
6. Computes viral scores (sum of normalized values)  
7. Determines **Positive/Negative** for each target  
8. Saves normalized ROI data as a CSV file  
9. Exposes REST endpoints:

| Endpoint            | Function |
|--------------------|----------|
| `POST /api/capture` | Acquire and return a new frame |
| `POST /api/extract` | Perform ROI extraction + scoring |
| `GET /download/...` | Download CSV output |

---

### 2.3 Web UI (HTML/CSS/JS)
The browser UI (index.html + style.css + app.js):

- Displays the sensor image with color-coded ROI boxes  
- Allows pixel-level adjustment of each ROI  
- Provides **RUN** and **Extract & Analyze** buttons  
- Shows Internal control status and viral Positive/Negative calls  
- Provides **Download CSV** for normalized ROI values  

Runs entirely in the browser—no installation needed.

---

### 2.4 Firebase (Optional)
Some deployments use Firebase Firestore to sync results across devices.  
Firebase is **not required** for reproducing the analysis pipeline.  
Service account keys are intentionally **not included** in this repository.

To enable Firebase (optional):


---

## 3. How to Run (From a Clean Machine)

### 3.1 Install Python dependencies
```bash
cd backend
pip install -r requirements.txt

3.2 Connect the MCU

Upload the example firmware or your own 160×160 pixel streaming firmware

Update PORT_NAME inside server.py if needed (e.g., "COM7" or "/dev/ttyACM0")

3.3 Run the Flask backend
python server.py

Running on http://127.0.0.1:5050

3.4 Open the Web UI

Open a browser and navigate to:

➡ http://127.0.0.1:5050

Then:

RUN — captures a new frame

Adjust ROIs if needed

Extract & Analyze — performs scoring

Download the CSV for record-keeping or offline analysis

4. Reproducibility Notes

The scoring method (ROI min–max normalization + sum of normalized pixels) is identical to the analysis used in the main experiments.

No filtering or temporal smoothing is applied at this layer.

CSV outputs contain the exact normalized ROI values used for viral score computation.

Example positive/negative CSV files are included under sample_data/.

5. Citation

If this code is used in a scientific publication, please cite:

Multicap Dx Web UI & Backend
Source code available at: https://github.com/USERNAME/MulticapDx

(Replace USERNAME with your GitHub account.)
