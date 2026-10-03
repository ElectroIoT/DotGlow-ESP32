# Changelog

## 0.3.1 (2026-10-03)
- BOOT button double press rotates the display 180° (upside down) and back; the app has a matching switch.
- Docs: power from a 5 V / 1 A (or stronger) charger, not a computer USB port (dim / stuck / garbled display and
  restarts were all power); flash-pin warning for the ESP32 DevKit; `tools/display-test` for wiring checks.

## 0.3.0 (2026-10-02)
- Stopwatch: `stopwatch` op, stopwatch screen (MM:SS / HH:MM, tenths bar, blinking when paused), optional push
  button on GPIO4 (S3) / GPIO13 (ESP32).

## 0.2.0 (2026-10-02)
- Firmware updates over Bluetooth (`ota/begin`, OTA characteristic, `ota/end`), progress bar on the display.
  Writes without response + a 7.5-15 ms connection interval: 1.2 MB in about 26 s.
- INFO reports the release asset and Bluetooth-update support.
- Links that never get encrypted are dropped after 60 s (a phone could get locked out by one).
- The clock keeps advertising while connected, so a reopened app always gets back in.
- `tools/release.py`: app images, full images for USB flashing, `firmware.json` for the app.
- ESP32-S3 builds use a 4 MB flash header (run on every S3 module).

## 0.1.0 (2026-10-02)
- ESP32 / ESP32-S3 port of the ESP8266 Matrix Clock: web dashboard, WiFi setup hotspot, animations, night mode,
  light sensor, messages, special days, login, 4-16 modules, GitHub updates, safe mode.
- Bluetooth LE service with PIN pairing (shown on the display) and the shared command layer (`api.cpp`).
