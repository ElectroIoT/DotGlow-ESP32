// Stopwatch: optional button on PIN_STOPWATCH (to GND), and the "stopwatch" API op.
#pragma once

#include <Arduino.h>

void     stopwatchBegin();                          // set up the button pin
bool     stopwatchLoop();                           // true while the stopwatch owns the display
bool     stopwatchCommand(const String& action);    // start, pause, toggle, reset, open, exit
String   stopwatchJson();                           // {"on","run","ms"}
uint32_t stopwatchMs();
