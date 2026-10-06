# Releasing DotGlow firmware

1. Bump `FW_VERSION` in `src/config.h` (the line ending in `// bump for every release`).
2. Add the version to `CHANGELOG.md`.
3. Build the release files:
   ```bash
   python tools/release.py
   ```
   This builds `esp32dev` + `esp32s3` and writes, in `release/<version>/` (gitignored):

   | File | Use |
   |---|---|
   | `firmware-esp32.bin`, `firmware-esp32s3.bin` | App image: GitHub OTA, Bluetooth updates, web upload |
   | `dotglow-esp32-full.bin`, `dotglow-esp32s3-full.bin` | Bootloader + partitions + boot_app0 + app, flashed at `0x0` (USB) |
   | `version.txt` | Read by the clock's GitHub update check |

   and `release/firmware.json`, the catalog the app reads (URLs, sizes, MD5s; also the latest ESP8266 Matrix Clock
   release, downloaded with `gh`).

4. Publish for the **app** (works while the repo is private): upload `release/<version>/*` to
   `manoranjan.dev/dotglow/fw/<version>/` and `release/firmware.json` to `manoranjan.dev/dotglow/firmware.json`
   (Hostinger, `domains/manoranjan.dev/public_html/dotglow/`).
5. Publish for **clocks updating themselves**: a GitHub release on `ElectroIoT/DotGlow-ESP32` with tag `v<version>`
   and assets `version.txt`, `firmware-esp32.bin`, `firmware-esp32s3.bin`. Only works once the repo is public.
6. Publish for the **web flasher** (https://mtpcode.com/flash/) and the **PC flasher**: run
   `python tools/make_web_flasher.py` (copies the full images + ESP8266 firmware into the mtpcode repo's
   `public/flash/` and rewrites the two manifests), then commit + push the mtpcode repo (GitHub Actions deploys it).
   The PC flasher (`desktop-flasher/`) reads `firmware.json` from step 4, so it needs no extra step.
7. Test: a clock on the previous version should offer the update (app *Updates*), and a fresh board should install
   from the app's *Install firmware*.

## firmware.json format

```json
{
  "dotglow": {
    "version": "0.3.0",
    "boards": {
      "esp32s3": {"app": "https://.../firmware-esp32s3.bin", "appSize": 0, "appMd5": "",
                  "full": "https://.../dotglow-esp32s3-full.bin", "fullSize": 0, "fullMd5": ""},
      "esp32": {}
    }
  },
  "esp8266": {"name": "Matrix Clock for ESP8266", "version": "1.4.0", "full": "https://github.com/...", "fullSize": 0, "fullMd5": ""}
}
```

The app only accepts `https://` links and checks size + MD5 after downloading.
