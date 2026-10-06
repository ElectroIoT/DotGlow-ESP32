# DotGlow Flasher (PC)

Install DotGlow on an **ESP32, ESP32-S3 or ESP8266** board from a Windows / Linux / macOS PC: pick the board, press
**Install**. It finds the board, downloads the latest firmware (checked with a checksum) and writes it. No PlatformIO,
no Arduino, no phone.

- Window: `DotGlowFlasher.exe` (or `python dotglow_flasher.py`)
- Command line: `dotglow-flasher-cli.exe` (or `python dotglow_flasher.py <command>`)

## Window

1. Plug the board in with a **USB data cable** (some cables only charge). Unplug the display's 5 V wire from the board.
2. Start the program. If exactly one board is plugged in it is detected by itself (chip, MAC, flash size).
3. Press **Install firmware**. About 20-60 seconds. Done: open the DotGlow app to set the clock up.

| Option | What it does |
|---|---|
| Keep my WiFi and settings | Only the app is replaced; WiFi, pairing and settings stay. Only for an ESP32 / ESP32-S3 that already runs DotGlow (the program checks and falls back to a full install) |
| Erase everything first | Wipes the whole flash before installing. For a board that behaves strangely |
| Advanced: speed | 460800 baud by default; use 115200 with a long or thin cable |
| Advanced: your own .bin | Flash any `.bin` at any address instead of the latest release |

A full install erases WiFi settings and pairing; the board shows a new 6-digit PIN on its display.

## Command line

```bash
dotglow-flasher list                        # serial ports
dotglow-flasher detect                      # chip, MAC, flash size of the only ESP board
dotglow-flasher flash                       # download the latest firmware and install it (asks first)
dotglow-flasher flash --port COM5 --yes     # no questions
dotglow-flasher flash --update              # keep WiFi / settings
dotglow-flasher flash --file my.bin --addr 0x0
```

## Where the firmware comes from

`https://manoranjan.dev/dotglow/firmware.json`, the same catalog the phone app uses (URL, size and MD5 per board).
Downloads are cached in `~/.dotglow-flasher/cache`. ESP32 / ESP32-S3 get **DotGlow**; an ESP8266 gets the
[ESP8266 Matrix Clock](https://github.com/ElectroIoT/ESP8266-Matrix-Clock) (no Bluetooth, set up from its web page).
Other chips (S2, C3, ...) are not supported.

## Run from source

```bash
pip install -r requirements.txt
python dotglow_flasher.py
```

## Build the .exe

```bat
build.bat
```

Makes `dist\DotGlowFlasher.exe` (window, no console) and `dist\dotglow-flasher-cli.exe` with PyInstaller.
Files are 36 MB because Python and esptool are inside.

**Windows warnings.** The `.exe` files are not code-signed. SmartScreen shows "Windows protected your PC": *More info →
Run anyway*. With **Smart App Control** or an organisation's App Control policy switched on, Windows refuses unsigned
programs completely (this happened on the development PC). Options: sign the files with a code-signing certificate,
run `python dotglow_flasher.py`, or use the phone app to flash.

## Troubleshooting

| Problem | Fix |
|---|---|
| No board listed | Data cable, another USB port. CH340 / CP210x boards may need their USB driver |
| "Could not talk to the board" | Hold the **BOOT** button, press RESET once, release BOOT, press Detect. Take every wire off the board |
| Stops half way / board drops off USB | The display's 5 V must not come from the board. Short thick cable. Speed 115200 |
| Board not found as ESP32-S3 | The S3 USB port is "USB Serial Device (Espressif)"; hold BOOT while plugging in if it is not listed |
