#include "settings.h"
#include "config.h"
#include <Preferences.h>

// Stored as one blob in NVS. Changing the layout: append fields at the end of Settings,
// bump SETTINGS_VER and give the new fields defaults in settingsLoad(), like the other
// versioned blocks there. A different MAGIC wipes everything back to defaults.
static const uint32_t MAGIC = 0x44474C31;   // "DGL1"
static const uint8_t  SETTINGS_VER = 1;
static const char*    NS = "dotglow";
static const char*    KEY = "cfg";

Settings cfg;

void settingsDefaults() {
    memset(&cfg, 0, sizeof(cfg));
    cfg.magic       = MAGIC;
    cfg.ver         = SETTINGS_VER;
    cfg.brightness  = DEF_BRIGHTNESS;
    cfg.nightFrom   = 22;
    cfg.nightTo     = 7;
    cfg.blinkColon  = 1;
    cfg.secondsBar  = 1;
    cfg.showDate    = 1;
    cfg.roll        = ROLL_DOWN;
    cfg.hourlyAnim  = ANIM_RANDOM;
    cfg.bootAnim    = ANIM_SPARKLE;
    cfg.autoUpdate  = 1;
    cfg.ldrMax      = 12;
    cfg.modules     = MATRIX_MODULES;
    cfg.hwType      = MATRIX_TYPE;
    cfg.flipH       = FLIP_HORIZONTAL;
    cfg.flipV       = FLIP_VERTICAL;
    cfg.showSecs    = 1;
    strlcpy(cfg.tz, DEF_TZ, sizeof(cfg.tz));
}

void settingsLoad() {
    Preferences p;
    p.begin(NS, false);   // read-write: creates the namespace on first boot
    size_t n = p.getBytesLength(KEY);
    // A shorter blob comes from an older layout: the fields it lacks keep their defaults.
    settingsDefaults();
    if (n >= offsetof(Settings, ver) + 1 && n <= sizeof(Settings)) {
        Settings stored;
        memset(&stored, 0, sizeof(stored));
        p.getBytes(KEY, &stored, n);
        if (stored.magic == MAGIC) memcpy(&cfg, &stored, n);
    }
    p.end();

    // never trust stored contents blindly
    cfg.magic = MAGIC;
    cfg.ver = SETTINGS_VER;
    cfg.ssid[sizeof(cfg.ssid) - 1] = 0;
    cfg.pass[sizeof(cfg.pass) - 1] = 0;
    cfg.tz[sizeof(cfg.tz) - 1] = 0;
    cfg.msg[sizeof(cfg.msg) - 1] = 0;
    if (!cfg.tz[0]) strlcpy(cfg.tz, DEF_TZ, sizeof(cfg.tz));
    if (cfg.brightness > 15) cfg.brightness = DEF_BRIGHTNESS;
    if (cfg.nightFrom > 23) cfg.nightFrom = 22;
    if (cfg.nightTo > 23) cfg.nightTo = 7;
    if (cfg.nightBr > 16) cfg.nightBr = 0;
    if (cfg.roll > ROLL_RANDOM) cfg.roll = ROLL_DOWN;
    if (cfg.hourlyAnim > ANIM_RANDOM) cfg.hourlyAnim = ANIM_OFF;
    if (cfg.bootAnim > ANIM_RANDOM) cfg.bootAnim = ANIM_OFF;
    if (cfg.msgEvery > 60) cfg.msgEvery = 0;
    if (cfg.ldrMin > 15) cfg.ldrMin = 0;
    if (cfg.ldrMax > 15) cfg.ldrMax = 12;
    if (cfg.modules < MIN_MODULES || cfg.modules > MAX_MODULES) cfg.modules = MATRIX_MODULES;
    if (cfg.hwType > MT_ICSTATION) cfg.hwType = MATRIX_TYPE;
    for (uint8_t* flag : {&cfg.fmt24, &cfg.autoDim, &cfg.leadingZero, &cfg.blinkColon, &cfg.secondsBar, &cfg.showDate,
                          &cfg.autoUpdate, &cfg.ldrOn, &cfg.ldrInvert, &cfg.flipH, &cfg.flipV, &cfg.showSecs})
        *flag = *flag ? 1 : 0;
    for (Event& e : cfg.events) {
        e.text[sizeof(e.text) - 1] = 0;
        if (e.month > 12 || e.day > 31 || e.anim > ANIM_RANDOM) memset(&e, 0, sizeof(e));
    }
}

void settingsSave() {
    Preferences p;
    p.begin(NS, false);
    p.putBytes(KEY, &cfg, sizeof(cfg));
    p.end();
}
