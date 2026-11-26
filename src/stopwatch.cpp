#include "stopwatch.h"
#include "config.h"
#include "countdown.h"
#include "display.h"
#include "settings.h"
#include "sound.h"

// Stopwatch, driven by the app / web API and the optional push button:
//
//   tap  -> clock showing: open the stopwatch and start; stopwatch showing: start / pause
//   hold -> running or paused with time: reset to 0;  already at 0: back to the clock

static const uint32_t IDLE_EXIT_MS = 30UL * 60 * 1000;   // paused this long: back to the clock

static bool     active  = false;
static bool     running = false;
static uint32_t startedAt = 0;   // millis() when it last started running
static uint32_t stored = 0;      // ms counted before that
static uint32_t idleSince = 0;

uint32_t stopwatchMs() { return stored + (running ? millis() - startedAt : 0); }

static void swStart() {
    if (running) return;
    running = true;
    startedAt = millis();
    soundCue(cfg.swSound, CUE_START);
}

static void swPause() {
    if (!running) return;
    stored = stopwatchMs();
    running = false;
    idleSince = millis();
    soundCue(cfg.swSound, CUE_PAUSE);
}

static void swReset() { running = false; stored = 0; idleSince = millis(); }

static void swOpen() {
    countdownClose();   // one of the two at a time on the display
    active = true;
    swReset();
}

static void swClose() { active = false; swReset(); }

static void swResetCued() {
    if (running || stored) soundCue(cfg.swSound, CUE_RESET);
    swReset();
}

bool stopwatchCommand(const String& action) {
    if      (action == "start")  { if (!active) swOpen(); swStart(); }
    else if (action == "pause")  swPause();
    else if (action == "toggle") { if (!active) { swOpen(); swStart(); } else if (running) swPause(); else swStart(); }
    else if (action == "reset")  { if (!active) swOpen(); swResetCued(); }
    else if (action == "open")   { if (!active) swOpen(); }
    else if (action == "exit")   swClose();
    else return false;
    return true;
}

void stopwatchButton(bool hold) {
    if (!hold || !active) stopwatchCommand("toggle");
    else if (running || stored) swResetCued();
    else swClose();
}

String stopwatchJson() {
    return String("{\"on\":") + (active ? "true" : "false") + ",\"run\":" + (running ? "true" : "false") +
           ",\"ms\":" + stopwatchMs() + "}";
}

bool stopwatchLoop() {
    if (!active) return false;
    if (!running && millis() - idleSince > IDLE_EXIT_MS) { swClose(); return false; }
    static uint32_t lastFrame = 0;
    if (millis() - lastFrame >= 30) {
        lastFrame = millis();
        drawStopwatch(stopwatchMs(), running);
    }
    return true;
}
