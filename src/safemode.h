// Safe mode: after several crashes in a row the clock starts with only WiFi, the
// update page and GitHub updates, so a bad firmware can be replaced over WiFi.
#pragma once

bool safeModeCheck();    // call first thing in setup(); true = start in safe mode
void safeModeStable();   // call once the firmware has run fine for a while
void restart();          // deliberate restart

// Updates are installed right after a restart, before the clock starts its features:
// a clean start is the most predictable state for a firmware download.
void restartToUpdate();  // restart, then install the waiting GitHub update
bool takeUpdateRequest();// true once after restartToUpdate()
