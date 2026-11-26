// Alarm clock: rings at the saved times (settings), with snooze. Needs a synced time.
#pragma once

#include <Arduino.h>

void   alarmLoop();                            // call every loop pass: starts and ends ringing
bool   alarmRinging();
void   alarmSnooze();                          // quiet now, ring again in cfg.snoozeMin minutes
void   alarmStop();                            // stop ringing and drop a pending snooze
void   alarmChanged(int slot);                 // a slot was edited or deleted: forget its ringing / snooze
bool   alarmCommand(const String& action);     // stop, snooze
String alarmJson();                            // {"ring","i","h","m","snooze"}
void   alarmFrame();                           // draw the ringing screen (call every loop pass)
