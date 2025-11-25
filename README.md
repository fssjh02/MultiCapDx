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

