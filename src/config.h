// DotGlow -- build-time configuration
#pragma once

#ifdef CRASH_TEST
#define FW_VERSION      "0.0.1"               // safe-mode test build (env:crashtest): always older than any release
#else
#define FW_VERSION      "0.3.1"               // bump for every release (tools/release.py reads it from here)
#endif

#include <MD_MAX72xx.h>

#if CONFIG_IDF_TARGET_ESP32S3
#define BOARD_NAME      "ESP32-S3"
#else
#define BOARD_NAME      "ESP32"
#endif

// ---- Display wiring (MAX7219 8x8 modules, chained) ---------------------------
// Hardware SPI (the board's default SPI pins):
//              ESP32 DevKit    ESP32-S3 DevKitC-1
//   CLK  ->    GPIO18          GPIO12
//   DIN  ->    GPIO23          GPIO11
//   CS   ->    GPIO5           GPIO10
//   VCC  ->    5V (VIN)        5V
#if CONFIG_IDF_TARGET_ESP32S3
#define PIN_CS          10
#else
#define PIN_CS          5
#endif
// Defaults only: module count, type and orientation are set on the web page / in the app.
#define MATRIX_TYPE     MT_FC16               // MT_FC16 (common blue 4-in-1), MT_GENERIC, MT_PAROLA, MT_ICSTATION
#define MATRIX_MODULES  4                     // 4 x 8 = 32 columns; up to 16
#define FLIP_VERTICAL   0                     // 1 = flip top-bottom
#define FLIP_HORIZONTAL 0                     // 1 = mirror left-right (both = upside down)

// ---- Button ------------------------------------------------------------------
// The BOOT button on both DevKits. Short press = scroll IP, double press = rotate 180, hold 5 s = WiFi setup,
// hold 10 s = remove the settings password.
#define PIN_BUTTON      0
#define BUTTON_HOLD_MS  5000
#define BUTTON_PASS_MS  10000
#define DOUBLE_PRESS_MS 450                   // two short presses within this = rotate the display 180

// ---- Optional stopwatch button (push button from the pin to GND) ---------------------
// Tap: start / pause (from the clock: open the stopwatch). Hold: reset, then back to the clock.
#if CONFIG_IDF_TARGET_ESP32S3
#define PIN_STOPWATCH   4
#else
#define PIN_STOPWATCH   13
#endif

// ---- Optional light sensor (LDR from 3V3 to the pin, 10k from the pin to GND) -------
#if CONFIG_IDF_TARGET_ESP32S3
#define PIN_LDR         1                     // ADC1 channel 0
#else
#define PIN_LDR         34                    // ADC1 channel 6 (input-only pin)
#endif

// ---- Network -----------------------------------------------------------------
#define AP_PREFIX       "DotGlow-"            // setup hotspot name, followed by 4 chip-ID hex digits
#define HOSTNAME        "dotglow"             // http://dotglow.local
#define WIFI_CONNECT_MS 20000                 // give up on the saved network after this long and open setup
#define WIFI_RETRY_MS   120000                // while in setup mode, retry the saved network this often
#define NTP_SERVER_1    "in.pool.ntp.org"
#define NTP_SERVER_2    "time.google.com"
#define NTP_SERVER_3    "pool.ntp.org"

// ---- Safe mode -----------------------------------------------------------------
// After this many crashes in a row the clock starts in safe mode (WiFi + update page only).
#define SAFE_MODE_CRASHES   3
#define SAFE_MODE_STABLE_MS 120000            // running this long counts as "not crashing"
#define SAFE_MODE_CHECK_MS  1800000           // in safe mode, look for a fixed release this often

// ---- Updates -------------------------------------------------------------------
// The clock installs new releases published at github.com/<GITHUB_REPO>/releases.
// Each release has one firmware file per chip plus version.txt (see tools/release.sh).
#define GITHUB_REPO     "ElectroIoT/DotGlow-ESP32"
#if CONFIG_IDF_TARGET_ESP32S3
#define FIRMWARE_ASSET  "firmware-esp32s3.bin"
#else
#define FIRMWARE_ASSET  "firmware-esp32.bin"
#endif
#define AUTO_UPDATE_HOUR 3                    // nightly check at 03:xx local time
#define BOOT_UPDATE_DELAY_MS 60000            // after power-on, install a waiting update after this long
#define OTA_RETRY_MS    2700000               // failed for a temporary reason: retry after 45 min
#define OTA_RETRIES     6                     // ... at most this many times per power-on

// Password for uploading a .bin from the web page. Only its SHA-256 is compiled in, taken
// from src/private_config.h (not in git); without it, manual upload is disabled.
#if __has_include("private_config.h")
#include "private_config.h"
#endif
#ifndef UPDATE_PASS_SHA256
#define UPDATE_PASS_SHA256 ""
#endif

// ---- Welcome text ----------------------------------------------------------------
// Scrolls at every power-on. Fixed in the firmware on purpose: it is not a setting.
#define WELCOME_TEXT    "manoranjan.dev"

// ---- Defaults for first boot / factory reset ---------------------------------------
#define DEF_TZ          "IST-5:30"            // POSIX TZ string, India
#define DEF_BRIGHTNESS  4                     // 0..15
