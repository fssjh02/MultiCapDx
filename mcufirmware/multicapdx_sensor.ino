/*
 * Multicap Dx – MCU Firmware (Fingerprint Sensor Readout)
 * Streams 160×160 = 25600 grayscale pixel values (0–255)
 * Triggered by a serial command from the Python Flask backend.
 *
 * Output format:
 *   v1 v2 v3 v4 ... v25600\n
 *
 * This format is required for compatibility with backend/server.py
 */

#include <DFRobot_ID809.h>

#define FPSerial   Serial1   // Fingerprint sensor hardware serial
#define switchPin  0         // Analog output pin (alternate signal)
#define relayPin   8         // Relay controlling the sensor power

uint8_t data[25600];         // 160×160 pixel buffer
int analogVal = 1;           // Toggles analog output signal

DFRobot_ID809 fingerprint;

void setup() {
  Serial.begin(9600);        // Communication with PC (Flask)
  FPSerial.begin(115200);    // Communication with sensor

  fingerprint.begin(FPSerial);

  analogWriteResolution(10); // Allows analogWrite up to 1023
  pinMode(relayPin, OUTPUT);

  // Start with sensor power ON
  digitalWrite(relayPin, HIGH);
  delay(100);
}

void loop() {

  fingerprint.enterStandbyState();   // Put module into low-power mode
  digitalWrite(relayPin, LOW);       // Power OFF sensor

  // Wait until ANY non-zero number is received from Flask
  while (Serial.readString().toInt() == 0);

  // Power ON the sensor
  digitalWrite(relayPin, HIGH);

  // Slight delay for sensor startup
  delay(200);

  // Toggle analog switching signal
  if (analogVal == 1) {
    analogWrite(switchPin, 1023);
    analogVal = 2;
  } else {
    analogWrite(switchPin, 1000);
    analogVal = 1;
  }

  // ---- Acquire 160×160 fingerprint image ----
  fingerprint.getFingerImage(data);

  // ---- Stream 25,600 grayscale values ----
  for (uint16_t i = 0; i < 25600; i++) {
    Serial.print(data[i]);
    Serial.print(" ");
  }
  Serial.println();

  delay(200);  // Small gap before next trigger
}
