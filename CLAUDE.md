# DotGlow firmware: brief for AI assistants

ESP32 / ESP32-S3 + MAX7219 LED matrix clock with WiFi, a web dashboard and a Bluetooth LE service for the Android
app **DotGlow** (separate repo `ElectroIoT/DotGlow-Android`, local `D:\My Project\Android\DotGlow`).
It grew out of `ElectroIoT/ESP8266-Matrix-Clock` (same features, ESP8266, no Bluetooth).

Read first: `docs/ARCHITECTURE.md` (modules, loop, settings), `docs/PROTOCOL.md` (BLE + every op),
`docs/DEVELOPMENT.md` (build, test, gotchas), `docs/RELEASE.md`.

## Commands

```bash
python -m platformio run -e esp32s3_test -t upload --upload-port COM5   # test build, PIN on serial
python -m platformio run -e esp32s3 -e esp32dev                          # release builds
python tools/release.py                                                  # release images + firmware.json
python tools/make_images.py                                              # README SVGs in docs/
```

## Rules that matter

- **Clean-room**: never copy code from other clock projects (e.g. schreibfaul1). Only the libraries in README credits.
- **One command layer**: every feature is an op in `api.cpp` `apiCall()`, used by both web (`/api/<op>`) and BLE.
  Keep the app (`DemoClock`, `ClockViewModel`) and `docs/PROTOCOL.md` in sync with any new op or config key.
- **Settings blob**: append fields only; default in `settingsDefaults()`, range check in `settingsValidate()`.
- **No slow work in web handlers or the BLE host task**: set a flag, do it in the main loop.
- **Pairing PIN only on the display** in release builds. `-DPIN_TO_SERIAL` is for `esp32s3_test` only.
- Welcome text `WELCOME_TEXT` ("manoranjan.dev") is permanent by design (not a setting).
- Display pictures exist three times and must match: `src/display.cpp`, `tools/make_images.py`,
  the app's `ui/matrix/Scenes.kt`.
- Bump `FW_VERSION` for every release; add to `CHANGELOG.md`.

## Hardware / environment

- Test board: ESP32-S3 N16R8 on COM5 (USB `303A:1001`), Bluetooth name DotGlow-EEA8. The PC has no Bluetooth;
  BLE is tested with a phone (Motorola Edge 40 Neo, adb `ZD222M4292`).
- Open COM5 with DTR/RTS **low** before `open()`. Stop serial loggers before uploading.
- Firmware for the app is hosted at `https://manoranjan.dev/dotglow/` (repo is private); SSH deploy details are in
  the user's `~/.ssh/dmt_deploy_info.txt`.

## Commits

Author `manoranjan2050 <manoranjan2050@live.com>`, trailer `Co-Authored-By: ElectroIoT <electroiot.in@gmail.com>`,
**no AI co-author trailer**. Commit after each finished step. Push as the `ElectroIoT` gh account, then switch back
to `manoranjan2050`.
