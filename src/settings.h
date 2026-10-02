// Persistent settings (one blob in the ESP32's NVS key-value storage)
#pragma once

#include <Arduino.h>

enum Anim : uint8_t { ANIM_OFF, ANIM_SPARKLE, ANIM_WIPE, ANIM_RAIN, ANIM_BOXES, ANIM_PACMAN, ANIM_RANDOM };
// MAX7219 module board types (MD_MAX72XX hardware types). Stored in flash: only append.
enum MatrixType : uint8_t { MT_FC16, MT_GENERIC, MT_PAROLA, MT_ICSTATION };
static const uint8_t MIN_MODULES = 4, MAX_MODULES = 16;

// Digit change animation. Values are stored in flash: only ever append.
enum Roll : uint8_t { ROLL_DOWN, ROLL_UP, ROLL_NONE, ROLL_DISSOLVE, ROLL_SLIDE, ROLL_FLIP, ROLL_DROP, ROLL_RANDOM };

// A yearly special day (birthday, anniversary...). month 0 = empty slot.
struct Event {
    uint8_t month;          // 1..12
    uint8_t day;            // 1..31
    uint8_t anim;           // Anim played before the text
    char    text[41];
};
static const int MAX_EVENTS = 8;

struct Settings {
    uint32_t magic;
    char     ssid[33];
    char     pass[65];
    uint8_t  brightness;    // 0..15
    uint8_t  autoDim;       // night mode on/off
    uint8_t  nightFrom;     // hour 0..23
    uint8_t  nightTo;       // hour 0..23
    uint8_t  nightBr;       // 0..15, 16 = display off
    uint8_t  fmt24;
    uint8_t  leadingZero;
    uint8_t  blinkColon;
    uint8_t  secondsBar;    // thin progress line under the digits
    uint8_t  showDate;      // scroll the date once a minute
    uint8_t  roll;          // Roll
    uint8_t  hourlyAnim;    // Anim
    uint8_t  bootAnim;      // Anim
    char     tz[48];
    uint8_t  ver;           // layout version; append new fields at the end and bump SETTINGS_VER
    uint8_t  autoUpdate;    // install new GitHub releases by itself at night
    uint8_t  msgEvery;      // minutes between repeats of msg, 0 = off
    char     msg[65];       // custom scrolling message
    Event    events[MAX_EVENTS];
    uint8_t  ldrOn;         // auto brightness from a light sensor (LDR) on PIN_LDR
    uint8_t  ldrMin;        // brightness in the dark, 0..15
    uint8_t  ldrMax;        // brightness in bright light, 0..15
    uint8_t  ldrInvert;     // sensor wired the other way round
    uint8_t  adminHash[32]; // SHA-256(adminSalt + settings password); all zero = no password
    uint8_t  adminSalt[16];
    uint8_t  sessionKey[16];// login cookie value, renewed on every password change
    uint8_t  modules;       // 8x8 modules in the chain, MIN_MODULES..MAX_MODULES
    uint8_t  hwType;        // MatrixType
    uint8_t  flipH;         // mirror left-right
    uint8_t  flipV;         // flip top-bottom (both flips = upside down)
    uint8_t  showSecs;      // show :SS when the display is wide enough
};

extern Settings cfg;

void settingsLoad();
void settingsSave();
void settingsDefaults();       // resets everything, including WiFi
