// Countdown timer: counts down to zero and rings. The "timer" API op and the optional button.
#pragma once

#include <Arduino.h>

void   countdownTick();                         // call every loop pass: notices the end
bool   countdownLoop();                         // true while the countdown owns the display
bool   countdownOn();
bool   countdownRinging();
void   countdownClose();                        // also ends the ringing
void   countdownButton(bool hold);              // tap: start / pause, hold: reset, then close
bool   countdownCommand(const String& action);  // start, pause, toggle, reset, open, exit, stop
bool   countdownSet(uint32_t seconds);          // 1 .. 99:59:59; opens the countdown, not started
String countdownJson();                         // {"on","run","ring","ms","total"}
