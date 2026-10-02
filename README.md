# DotGlow (ESP32)

WiFi + Bluetooth LED-matrix clock firmware for **ESP32** and **ESP32-S3** with MAX7219 8x8 modules
(4-16 in a chain). The companion Android app, *DotGlow: LED Matrix Clock*, sets everything up over Bluetooth.

> **Status: in development.** Phase 1 (ESP32 port of the
> [ESP8266 Matrix Clock](https://github.com/ElectroIoT/ESP8266-Matrix-Clock)) builds and boots on an
> ESP32-S3. Bluetooth and the app come next.

## Roadmap

| Phase | What | Status |
|---|---|---|
| 1 | ESP32 / ESP32-S3 port: same features as the ESP8266 clock (web dashboard, phone WiFi setup, animations, night mode, messages, special days, login, multi-display, GitHub updates, safe mode) | 🟡 builds, boots, setup hotspot up; full hardware test pending |
| 2 | Bluetooth (BLE) settings service + protocol spec ([docs/PROTOCOL.md](docs/PROTOCOL.md)) | ✅ paired and tested with a Motorola Edge 40 Neo (Android 15) |
| 3 | Android app: pairing (PIN shown on the LED display), dashboard | ✅ ([DotGlow-Android](https://github.com/ElectroIoT/DotGlow-Android)) |
| 4 | Android app: all settings, WiFi setup, app PIN lock, setup guide | ✅ |
| 5 | Firmware updates over Bluetooth from the app (`ota/*`, see [docs/PROTOCOL.md](docs/PROTOCOL.md)) | ✅ tested on a phone: 1.2 MB in 26 s (46 KB/s) |
| 6 | Flash a new board from the phone over USB-OTG (ESP32, ESP32-S3, and the ESP8266 clock); full images from `tools/release.py` | ✅ flasher tested on an ESP32-S3 (1.3 MB in 18 s, MD5 verified) |
| 7 | Release | ⬜ |

## Wiring

| MAX7219 | ESP32 DevKit | ESP32-S3 DevKitC-1 |
|---|---|---|
| VCC | 5V (VIN) | 5V |
| GND | GND | GND |
| DIN | GPIO23 | GPIO11 |
| CS | GPIO5 | GPIO10 |
| CLK | GPIO18 | GPIO12 |

Optional light sensor (LDR from 3V3 to the pin, 10 kΩ from the pin to GND): GPIO34 (ESP32) / GPIO1 (ESP32-S3).
The **BOOT** button: short press shows the IP, hold 5 s for WiFi setup, hold 10 s to remove the settings password.

> The ESP32-S2 has no Bluetooth and is not supported.

## Build

```bash
pio run -e esp32s3 -t upload     # ESP32-S3
pio run -e esp32dev -t upload    # classic ESP32
```

## Credits

Based on the author's own [ESP8266 Matrix Clock](https://github.com/ElectroIoT/ESP8266-Matrix-Clock) (MIT).
Uses [MD_MAX72XX](https://github.com/MajicDesigns/MD_MAX72XX) by Marco Colli (LGPL-2.1) and the
[Arduino-ESP32 core](https://github.com/espressif/arduino-esp32) (LGPL-2.1).

## License

MIT, see [LICENSE](LICENSE). Made by [manoranjan.dev](https://manoranjan.dev).
