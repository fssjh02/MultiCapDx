# MCU Firmware – Multicap Dx

This folder contains the example microcontroller firmware used for the Multicap Dx system.  
The MCU communicates with the fingerprint-style 2D capacitance sensor (DFRobot ID809) and streams a **160×160 grayscale frame (25,600 pixels)** when triggered by the Python Flask backend.

## Trigger Mechanism
The backend sends a serial command: 

99\n

or any non-zero number.

When the MCU receives this signal:
1. The relay powers ON the sensor  
2. The sensor captures a frame  
3. The MCU streams all 25,600 grayscale pixel values in the format:

v1 v2 v3 v4 ... v25600


## Requirements
- DFRobot ID809 module
- Serial1 hardware interface
- 115200 baud sensor link
- 9600 baud PC link

## Compatibility
This output format is required by:

backend/server.py

and is fully compatible with the Web UI and ROI extraction pipeline.

---
