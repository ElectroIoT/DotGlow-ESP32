# Developing DotGlow firmware

## Build environments (`platformio.ini`)

| Env | Board | Notes |
|---|---|---|
| `esp32dev` | ESP32 DevKit (WROOM-32) | Release build |
| `esp32s3` | ESP32-S3 DevKitC-1 | Release build, serial log on the native USB port (`ARDUINO_USB_CDC_ON_BOOT=1`) |
| `esp32s3_test` | ESP32-S3 | Like `esp32s3` plus `-DPIN_TO_SERIAL`: the pairing PIN is printed on serial. **Never release it.** |
| `esp32dev_test` | ESP32 DevKit | Same for the classic ESP32 |

```bash
python -m platformio run -e esp32s3_test -t upload --upload-port COM5
python -m platformio run -e esp32s3 -e esp32dev          # both release builds
```

(`pio` may not be on PATH on the dev PC; `python -m platformio` always works.)

## Test hardware used so far

- ESP32-S3 N16R8 DevKitC-1 on **COM5**, native USB `303A:1001`, Bluetooth name **DotGlow-EEA8**.
- Phone: Motorola Edge 40 Neo, Android 15 (adb serial `ZD222M4292`). The dev PC has **no Bluetooth adapter**,
  so all BLE testing goes through a phone.

## Serial gotchas (ESP32-S3 native USB)

- Open the port with **DTR and RTS low before `open()`**, or the board resets / drops into download mode:
  ```python
  s = serial.Serial(); s.port = 'COM5'; s.baudrate = 115200; s.dtr = False; s.rts = False; s.open()
  ```
- Recover a board stuck in download mode: `python -m esptool --port COM5 --after hard-reset chip-id`.
- Only one program can hold COM5: stop any serial logger before `pio ... -t upload`.

## Pairing without a display

Flash `esp32s3_test`, watch serial for `BLE: pairing PIN nnnnnn (test build)` and type it into Android's
pairing dialog within ~30 s (the SMP timeout). With adb: tap the EditText, `adb shell input text nnnnnn`, tap OK.

A full USB flash wipes NVS, including the clock's pairing keys; the app then detects the stale pairing, removes it
and pairs again. `pio -t upload` (app only) keeps NVS.

## Testing with the app

- Real clock: DotGlow-Android, connect to DotGlow-EEA8.
- No hardware: the app's **demo clock** answers like the firmware (in-app, no BLE).
- The app's USB flasher can be run from the PC against the S3: see DotGlow-Android `FlasherHardwareTest`.

## README images

```bash
python tools/make_images.py      # writes docs/*.svg (animated, generated from the firmware's fonts and frames)
```

If you change digit styles, animations or the stopwatch face in `display.cpp`, change `tools/make_images.py`
(and the app's `ui/matrix/Scenes.kt`) the same way.

## Code style

- Comments explain *why*, short, in the existing tone. Keep functions small and the main loop non-blocking.
- New settings: append to `Settings`, default + validate, expose in `opConfig` / `opSet`, add to the app.
- New ops: add to `apiCall` (and `openOp` only if untrusted callers may use it), document in `docs/PROTOCOL.md`,
  add to the app's `DemoClock`.

## Commits

Author `manoranjan2050 <manoranjan2050@live.com>` with the trailer
`Co-Authored-By: ElectroIoT <electroiot.in@gmail.com>`. No AI co-author trailers. Push with the `ElectroIoT`
GitHub account (`gh auth switch -u ElectroIoT`), then switch back to `manoranjan2050`.
