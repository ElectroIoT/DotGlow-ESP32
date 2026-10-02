#include "stopwatch.h"
#include "config.h"
#include "display.h"

// Stopwatch: an optional push button from PIN_STOPWATCH to GND (internal pull-up, so with
// nothing connected the pin simply never reads "pressed"), and the app / web API.
//
//   tap  -> clock showing: open the stopwatch and start; stopwatch showing: start / pause
//   hold -> running or paused with time: reset to 0;  already at 0: back to the clock

static const uint32_t HOLD_MS = 1200;
static const uint32_t IDLE_EXIT_MS = 30UL * 60 * 1000;   // paused this long: back to the clock

static bool     active  = false;
static bool     running = false;
static uint32_t startedAt = 0;   // millis() when it last started running
static uint32_t stored = 0;      // ms counted before that
static uint32_t idleSince = 0;

uint32_t stopwatchMs() { return stored + (running ? millis() - startedAt : 0); }

static void swStart()  { if (!running) { running = true; startedAt = millis(); } }
static void swPause()  { if (running) { stored = stopwatchMs(); running = false; idleSince = millis(); } }
static void swReset()  { running = false; stored = 0; idleSince = millis(); }
static void swOpen()   { active = true; swReset(); }
static void swClose()  { active = false; swReset(); }

bool stopwatchCommand(const String& action) {
    if      (action == "start")  { if (!active) swOpen(); swStart(); }
    else if (action == "pause")  swPause();
    else if (action == "toggle") { if (!active) { swOpen(); swStart(); } else if (running) swPause(); else swStart(); }
    else if (action == "reset")  { if (!active) swOpen(); swReset(); }
    else if (action == "open")   { if (!active) swOpen(); }
    else if (action == "exit")   swClose();
    else return false;
    return true;
}

String stopwatchJson() {
    return String("{\"on\":") + (active ? "true" : "false") + ",\"run\":" + (running ? "true" : "false") +
           ",\"ms\":" + stopwatchMs() + "}";
}

void stopwatchBegin() {
    pinMode(PIN_STOPWATCH, INPUT_PULLUP);
}

static void readButton() {
    static bool     down = false, holdDone = false;
    static uint32_t downAt = 0, changedAt = 0;
    bool pressed = digitalRead(PIN_STOPWATCH) == LOW;
    if (pressed != down && millis() - changedAt > 30) {   // 30 ms debounce
        changedAt = millis();
        down = pressed;
        if (down) {
            downAt = millis();
            holdDone = false;
        } else if (!holdDone) {
            stopwatchCommand("toggle");   // a tap
        }
    }
    if (down && !holdDone && millis() - downAt >= HOLD_MS && active) {
        holdDone = true;
        if (running || stored) swReset(); else swClose();
    }
}

bool stopwatchLoop() {
    readButton();
    if (!active) return false;
    if (!running && millis() - idleSince > IDLE_EXIT_MS) { swClose(); return false; }
    static uint32_t lastFrame = 0;
    if (millis() - lastFrame >= 30) {
        lastFrame = millis();
        drawStopwatch(stopwatchMs(), running);
    }
    return true;
}
