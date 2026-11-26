#include "countdown.h"
#include "alarm.h"
#include "app.h"
#include "config.h"
#include "display.h"
#include "settings.h"
#include "sound.h"
#include "stopwatch.h"

static const uint32_t MAX_SECONDS = 99UL * 3600 + 59 * 60 + 59;
static const uint32_t IDLE_EXIT_MS = 30UL * 60 * 1000;   // not running this long: back to the clock

static bool     active = false;
static bool     running = false;
static bool     ringing = false;
static uint32_t total = TIMER_DEF_S * 1000UL;
static uint32_t remaining = TIMER_DEF_S * 1000UL;   // ms left when it last started or paused
static uint32_t startedAt = 0;
static uint32_t idleSince = 0;
static uint32_t ringStart = 0;

static uint32_t left() {
    if (!running) return remaining;
    const uint32_t gone = millis() - startedAt;
    return gone < remaining ? remaining - gone : 0;
}

bool countdownOn() {
    return active;
}

bool countdownRinging() {
    return ringing;
}

static void cdSilence() {
    if (!ringing) return;
    ringing = false;
    soundStop();
    applyBrightness(true);
}

static void cdOpen() {
    if (active) return;
    stopwatchCommand("exit");   // one of the two at a time on the display
    active = true;
    running = false;
    remaining = total;
    idleSince = millis();
}

void countdownClose() {
    cdSilence();
    active = running = false;
    remaining = total;
}

static void cdStart() {
    cdOpen();
    cdSilence();
    if (running) return;
    if (!remaining) remaining = total;
    running = true;
    startedAt = millis();
}

static void cdPause() {
    if (!running) return;
    remaining = left();
    running = false;
    idleSince = millis();
}

static void cdReset() {
    cdOpen();
    cdSilence();
    running = false;
    remaining = total;
    idleSince = millis();
}

bool countdownSet(uint32_t seconds) {
    if (!seconds || seconds > MAX_SECONDS) return false;
    total = seconds * 1000UL;
    cdReset();
    return true;
}

bool countdownCommand(const String& action) {
    if      (action == "start")  cdStart();
    else if (action == "pause")  cdPause();
    else if (action == "toggle") { if (running) cdPause(); else cdStart(); }
    else if (action == "reset")  cdReset();
    else if (action == "open")   cdOpen();
    else if (action == "exit")   countdownClose();
    else if (action == "stop")   { if (ringing) countdownClose(); }
    else return false;
    return true;
}

void countdownButton(bool hold) {
    if (!hold) countdownCommand("toggle");
    else if (running || remaining != total) cdReset();
    else countdownClose();
}

void countdownTick() {
    if (running && !left() && !alarmRinging()) {   // else: ring once the alarm is done
        running = false;
        remaining = 0;
        ringing = true;
        ringStart = millis();
        animRequest = ANIM_OFF;
        scrollRequest = "";
        applyBrightness(true);
        Serial.println(F("Countdown finished"));
        soundPlay(cfg.timerSound, true);
    }
    if (ringing && millis() - ringStart >= TIMER_RING_MS) countdownClose();
}

bool countdownLoop() {
    if (!active) return false;
    if (!running && !ringing && millis() - idleSince > IDLE_EXIT_MS) {
        countdownClose();
        return false;
    }
    static uint32_t lastFrame = 0;
    if (millis() - lastFrame >= 30) {
        lastFrame = millis();
        if (ringing) drawTimerEnd(millis() - ringStart);
        else         drawCountdown(left(), total, running);
    }
    return true;
}

String countdownJson() {
    return String("{\"on\":") + (active ? "true" : "false") + ",\"run\":" + (running ? "true" : "false") +
           ",\"ring\":" + (ringing ? "true" : "false") + ",\"ms\":" + left() + ",\"total\":" + total / 1000 + "}";
}
