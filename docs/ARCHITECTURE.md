# DotGlow firmware: architecture

Arduino framework on ESP-IDF (PlatformIO `espressif32@^6.9`, Arduino core 2.x), single sketch split into modules.
Clean-room code: nothing is copied from other clock projects. Only open-source libraries listed in the README.

## Source map (`src/`)

| File | Job |
|---|---|
| `config.h` | Build-time constants: `FW_VERSION`, pins per chip (`CONFIG_IDF_TARGET_ESP32S3`), names, NTP, OTA, defaults |
| `main.cpp` | `setup()` / `loop()`, WiFi connect, setup hotspot, clock / setup / safe loops, BOOT button, brightness, LDR |
| `app.h` | State shared between main and the transports: `appMode`, request flags (`animRequest`, `scrollRequest`, `otaRequest`, `digitDemo`, `moduleTest`), helpers |
| `settings.h/.cpp` | `Settings cfg`: one NVS blob (`Preferences`, key `cfg`), magic `DGL1`, append-only layout, `settingsValidate()` |
| `display.h/.cpp` | Frame buffer (one byte per column), MD_MAX72XX output, 5x7 digits, `ClockFace` (6 roll styles), animations, PIN / progress / stopwatch screens |
| `api.h/.cpp` | **One command layer** for web and Bluetooth: `apiCall(op, args, trusted)` -> `ApiResult{code, body, json}` |
| `web.h/.cpp`, `web_pages.h` | `WebServer`: pages, `/api/<op>` -> `apiCall`, login cookie, captive portal, password-protected `.bin` upload |
| `ble.h/.cpp` | NimBLE GATT service (see `docs/PROTOCOL.md`), pairing PIN, request queue, OTA characteristic, stale-link cleanup |
| `ota.h/.cpp` | GitHub releases: `version.txt` + `firmware-<chip>.bin`, `WiFiClientSecure` with `github_roots.h` CAs |
| `safemode.h/.cpp` | Crash counter in `RTC_NOINIT` memory + `esp_reset_reason()`; restart-to-update flag |
| `stopwatch.h/.cpp` | Stopwatch state, optional button (`PIN_STOPWATCH`), `stopwatch` op |
| `private_config.h` | Gitignored: `UPDATE_PASS_SHA256` for the web upload (`private_config.example.h` is the template) |

## Boot and modes

```
setup(): safeModeCheck -> settingsLoad -> displayBegin -> WiFi.mode(STA) -> webBegin -> bleBegin
         safe?  -> MODE_SAFE  (WiFi + update only)
         no WiFi / connect fails -> MODE_SETUP (hotspot DotGlow-XXXX + captive portal)
         else   -> MODE_CLOCK (NTP, mDNS dotglow.local, scroll IP)
loop():  service()            webLoop + bleLoop + scheduled restart
         handleButton()       BOOT button hints
         blePasskey -> drawPasskey        (pairing PIN wins the display)
         bleUpdateProgress -> drawProgress
         stopwatchLoop()      (owns the display while on)
         setupLoop / safeLoop / clockLoop
```

`WiFi.mode()` must run before the `WebServer` is created (lwip "Invalid mbox" assert otherwise).

## Long work runs in the main loop

Web handlers and the BLE host task never do slow work. They set a flag (`otaRequest`, `animRequest`, ...) or queue a
request; the main loop does it. BLE requests are parsed in the host task, queued (max 8), and run by `bleLoop()`.
Animations are blocking but call `serviceWait()`, which keeps web + BLE responsive.

The one exception is the BLE OTA data: `OtaCallbacks::onWrite` writes straight to `Update` in the host task; the
link layer throttles the phone while flash is busy.

## Settings

`Settings` in `settings.h` is saved as one blob. Rules: **append new fields at the end**, give them a default in
`settingsDefaults()` and a range check in `settingsValidate()`. Older blobs are shorter; the loader keeps defaults
for the missing tail. Config keys on the wire (`"br"`, `"fmt24"`, `"roll"`...) are listed in `api.cpp` `opConfig` /
`opSet` and must match the app.

## Security model

- Web: login cookie `mc_session` after the settings password (if set). Untrusted callers may only use `openOp()` ops.
- BLE: RX / TX / OTA need an encrypted + authenticated link (LE Secure Connections, MITM, bonding, display-only IO).
  The PIN is random per pairing and shown only on the display (`-DPIN_TO_SERIAL` test builds also print it).
- Links that are not encrypted after 60 s are dropped.
- Web `.bin` upload needs `UPDATE_PASS_SHA256`; empty = disabled.

## Updates

- GitHub: `https://github.com/ElectroIoT/DotGlow-ESP32/releases/latest/download/{version.txt,firmware-<chip>.bin}`.
  Installs happen on a fresh boot (`restartToUpdate()`) for maximum free heap. Needs the repo to be **public**.
- Bluetooth: `ota/begin` -> raw bytes on the OTA characteristic -> `ota/end` (size + MD5 checked).
- USB (new boards): full image from `tools/release.py`, written by the app's ROM-bootloader flasher.

## Partitions

`min_spiffs.csv`: two ~1.9 MB app slots (OTA), small SPIFFS (unused). S3 builds use a 4 MB flash header
(`board_upload.flash_size = 4MB`) so one image runs on every S3 module.
