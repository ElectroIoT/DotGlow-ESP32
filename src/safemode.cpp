#include "safemode.h"
#include "config.h"
#include <Arduino.h>
#include <esp_system.h>

// Kept in RTC memory that survives resets but not power loss, so unplugging the
// clock always gives the normal firmware another try.
static RTC_NOINIT_ATTR uint32_t rtcMagic;
static RTC_NOINIT_ATTR uint32_t rtcCrashes;
static RTC_NOINIT_ATTR uint32_t rtcInstallUpdate;
static const uint32_t MAGIC = 0x5AFE3201;

static bool wasCrash(esp_reset_reason_t r) {
    switch (r) {
        case ESP_RST_PANIC:      // exception, abort(), out of memory
        case ESP_RST_INT_WDT:
        case ESP_RST_TASK_WDT:
        case ESP_RST_WDT:
            return true;
        default:                 // power-on, reset button, ESP.restart(), deep sleep, brownout
            return false;        // (brownout = weak power supply, not a firmware bug)
    }
}

bool safeModeCheck() {
    if (rtcMagic != MAGIC) {
        rtcMagic = MAGIC;
        rtcCrashes = 0;
        rtcInstallUpdate = 0;
    }
    esp_reset_reason_t r = esp_reset_reason();
    rtcCrashes = wasCrash(r) ? rtcCrashes + 1 : 0;
    if (r == ESP_RST_POWERON) rtcInstallUpdate = 0;
    Serial.printf("Reset reason %d, crashes in a row: %u\n", (int)r, rtcCrashes);
    return rtcCrashes >= SAFE_MODE_CRASHES;
}

void safeModeStable() {
    rtcCrashes = 0;
}

void restart() {
    ESP.restart();
}

void restartToUpdate() {
    rtcInstallUpdate = 1;
    ESP.restart();
}

bool takeUpdateRequest() {
    if (!rtcInstallUpdate) return false;
    rtcInstallUpdate = 0;   // one attempt per request: a failed install must not loop
    return true;
}
