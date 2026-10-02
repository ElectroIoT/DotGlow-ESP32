// Bluetooth LE: the DotGlow app's connection to the clock. See docs/PROTOCOL.md.
#pragma once

#include <Arduino.h>

void bleBegin(const String& name);   // start the GATT service and advertising
void bleLoop();                      // handle queued requests (call from the main loop)
bool blePasskey(uint32_t& passkey);  // true while a pairing PIN should be on the display
void bleForgetPhones();              // remove every paired phone
