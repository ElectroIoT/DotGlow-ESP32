// Stopwatch: the optional button, and the "stopwatch" API op.
#pragma once

#include <Arduino.h>

void     stopwatchButton(bool hold);                // tap: start / pause, hold: reset, then close
bool     stopwatchLoop();                           // true while the stopwatch owns the display
bool     stopwatchCommand(const String& action);    // start, pause, toggle, reset, open, exit
String   stopwatchJson();                           // {"on","run","ms"}
uint32_t stopwatchMs();
