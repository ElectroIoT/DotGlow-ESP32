#include "alarm.h"
#include "app.h"
#include "config.h"
#include "countdown.h"
#include "display.h"
#include "settings.h"
#include "sound.h"
#include <time.h>

static int      slot = -1;        // the alarm that is ringing or snoozed, -1 = none
static bool     ringing = false;
static uint32_t ringStart = 0;
static uint32_t snoozeAt = 0;     // millis() to ring again, 0 = not snoozed

static void ring() {
    if (countdownRinging()) countdownClose();   // one thing rings at a time
    ringing = true;
    ringStart = millis();
    snoozeAt = 0;
    animRequest = ANIM_OFF;       // nothing queued may interrupt the alarm
    scrollRequest = "";
    applyBrightness(true);        // wakes a display that night mode switched off
    soundPlay(cfg.alarms[slot].sound, true);
}

static void quiet() {
    if (!ringing) return;
    ringing = false;
    soundStop();
    applyBrightness(true);
}

bool alarmRinging() {
    return ringing;
}

void alarmSnooze() {
    if (!ringing) return;
    quiet();
    snoozeAt = (millis() + cfg.snoozeMin * 60000UL) | 1;
    scrollRequest = String("Snooze ") + cfg.snoozeMin + " min";
}

void alarmStop() {
    quiet();
    snoozeAt = 0;
    slot = -1;
}

void alarmChanged(int i) {
    if (i == slot) alarmStop();
}

// Today's bit in Alarm::days (bit 0 = Monday; tm_wday 0 = Sunday)
static uint8_t dayBit(const struct tm& t) {
    return 1 << ((t.tm_wday + 6) % 7);
}

void alarmLoop() {
    if (ringing && millis() - ringStart >= ALARM_RING_MS) alarmStop();
    if (snoozeAt && (int32_t)(millis() - snoozeAt) >= 0) ring();
    if (!timeValid()) return;

    static time_t lastMinute = 0;
    const time_t now = time(nullptr);
    if (now / 60 == lastMinute) return;   // each minute is looked at once
    lastMinute = now / 60;
    struct tm t;
    localtime_r(&now, &t);
    for (int i = 0; i < MAX_ALARMS; i++) {
        Alarm& a = cfg.alarms[i];
        if (!a.used || !a.on || a.hour != t.tm_hour || a.minute != t.tm_min) continue;
        if (a.days && !(a.days & dayBit(t))) continue;
        if (!a.days) {           // a one-time alarm switches itself off
            a.on = 0;
            settingsSave();
        }
        quiet();
        slot = i;
        Serial.printf("Alarm %d: %02u:%02u\n", i, a.hour, a.minute);
        ring();
        break;
    }
}

bool alarmCommand(const String& action) {
    if      (action == "stop")   alarmStop();
    else if (action == "snooze") alarmSnooze();
    else return false;
    return true;
}

String alarmJson() {
    const bool has = slot >= 0;
    const uint32_t left = snoozeAt ? (uint32_t)max<int32_t>(0, (int32_t)(snoozeAt - millis())) / 1000 : 0;
    return String("{\"ring\":") + (ringing ? "true" : "false") + ",\"i\":" + slot +
           ",\"h\":" + (has ? cfg.alarms[slot].hour : 0) + ",\"m\":" + (has ? cfg.alarms[slot].minute : 0) +
           ",\"snooze\":" + left + "}";
}

void alarmFrame() {
    static uint32_t last = 0;
    if (millis() - last < 40) return;
    last = millis();
    const time_t now = time(nullptr);
    struct tm t;
    localtime_r(&now, &t);
    drawAlarm(t, millis() - ringStart);
}
