#include "api.h"
#include "app.h"
#include "config.h"
#include "ota.h"
#include "settings.h"
#include <WiFi.h>
#include <esp_random.h>
#include <mbedtls/sha256.h>

// =================================================================================
// Helpers
// =================================================================================

String jsonStr(const String& s) {
    String o = "\"";
    for (size_t i = 0; i < s.length(); i++) {
        char c = s[i];
        if (c == '"' || c == '\\') { o += '\\'; o += c; }
        else if ((uint8_t)c < 0x20) o += ' ';
        else o += c;
    }
    return o + "\"";
}

bool apiHasPassword() {
    for (uint8_t b : cfg.adminHash)
        if (b) return true;
    return false;
}

void apiSha256(const uint8_t* a, size_t na, const uint8_t* b, size_t nb, uint8_t out[32]) {
    mbedtls_sha256_context ctx;
    mbedtls_sha256_init(&ctx);
#if MBEDTLS_VERSION_NUMBER >= 0x03000000
    mbedtls_sha256_starts(&ctx, 0);
    mbedtls_sha256_update(&ctx, a, na);
    mbedtls_sha256_update(&ctx, b, nb);
    mbedtls_sha256_finish(&ctx, out);
#else
    mbedtls_sha256_starts_ret(&ctx, 0);
    mbedtls_sha256_update_ret(&ctx, a, na);
    mbedtls_sha256_update_ret(&ctx, b, nb);
    mbedtls_sha256_finish_ret(&ctx, out);
#endif
    mbedtls_sha256_free(&ctx);
}

void apiHashPassword(const String& pw, const uint8_t salt[16], uint8_t out[32]) {
    apiSha256(salt, 16, (const uint8_t*)pw.c_str(), pw.length(), out);
}

bool apiSameBytes(const uint8_t* a, const uint8_t* b, size_t n) {
    uint8_t diff = 0;
    for (size_t i = 0; i < n; i++) diff |= a[i] ^ b[i];
    return diff == 0;
}

static ApiResult ok(const String& body = "OK") {
    ApiResult r;
    r.body = body;
    return r;
}

static ApiResult fail(int code, const String& msg) {
    ApiResult r;
    r.code = code;
    r.body = msg;
    return r;
}

static ApiResult json(const String& body) {
    ApiResult r;
    r.body = body;
    r.json = true;
    return r;
}

// =================================================================================
// Operations
// =================================================================================

static ApiResult opStatus(bool trusted) {
    char t[12] = "--:--", ap[4] = "", d[40] = "";
    if (timeValid()) {
        time_t now = time(nullptr);
        struct tm lt;
        localtime_r(&now, &lt);
        strftime(t, sizeof(t), cfg.fmt24 ? "%H:%M:%S" : "%I:%M:%S", &lt);
        if (!cfg.leadingZero && t[0] == '0') memmove(t, t + 1, strlen(t));
        if (!cfg.fmt24) strftime(ap, sizeof(ap), "%p", &lt);
        strftime(d, sizeof(d), "%A, %d %B %Y", &lt);
    }
    bool sta = WiFi.status() == WL_CONNECTED;
    return json(String("{\"time\":") + jsonStr(t) + ",\"ampm\":" + jsonStr(ap) + ",\"date\":" + jsonStr(d) +
                ",\"synced\":" + (timeValid() ? "true" : "false") +
                ",\"ssid\":" + jsonStr(sta && trusted ? WiFi.SSID() : String()) +   // no network name before login
                ",\"ip\":" + jsonStr(sta ? WiFi.localIP().toString() : WiFi.softAPIP().toString()) +
                ",\"rssi\":" + String(sta ? WiFi.RSSI() : 0) + ",\"up\":" + String(millis() / 1000) +
                ",\"version\":" + jsonStr(FW_VERSION) + ",\"board\":" + jsonStr(BOARD_NAME) +
                ",\"latest\":" + jsonStr(ota.latest) +
                ",\"newer\":" + (ota.latest.length() && otaNewer(ota.latest) ? "true" : "false") +
                ",\"otaMsg\":" + jsonStr(ota.message) + ",\"otaBusy\":" + (otaRequest ? "true" : "false") +
                ",\"mode\":" + jsonStr(appMode == MODE_SETUP ? "setup" : appMode == MODE_SAFE ? "safe" : "clock") +
                ",\"safe\":" + (appMode == MODE_SAFE ? "true" : "false") +
                ",\"light\":" + String(lightPercent()) + ",\"brNow\":" + String(brightnessNow()) + "}");
}

static ApiResult opConfig() {
    String j = String("{\"br\":") + cfg.brightness + ",\"autoDim\":" + cfg.autoDim + ",\"nightFrom\":" + cfg.nightFrom +
               ",\"nightTo\":" + cfg.nightTo + ",\"nightBr\":" + cfg.nightBr + ",\"fmt24\":" + cfg.fmt24 +
               ",\"leadingZero\":" + cfg.leadingZero + ",\"blinkColon\":" + cfg.blinkColon +
               ",\"secondsBar\":" + cfg.secondsBar + ",\"showDate\":" + cfg.showDate + ",\"roll\":" + cfg.roll +
               ",\"hourlyAnim\":" + cfg.hourlyAnim + ",\"bootAnim\":" + cfg.bootAnim +
               ",\"tz\":" + jsonStr(cfg.tz) + ",\"ssid\":" + jsonStr(cfg.ssid) +
               ",\"autoUpdate\":" + cfg.autoUpdate + ",\"msg\":" + jsonStr(cfg.msg) + ",\"msgEvery\":" + cfg.msgEvery +
               ",\"pinUpload\":" + (strlen(UPDATE_PASS_SHA256) ? "true" : "false") +
               ",\"ldrOn\":" + cfg.ldrOn + ",\"ldrMin\":" + cfg.ldrMin + ",\"ldrMax\":" + cfg.ldrMax +
               ",\"ldrInvert\":" + cfg.ldrInvert + ",\"modules\":" + cfg.modules + ",\"hwType\":" + cfg.hwType +
               ",\"flipH\":" + cfg.flipH + ",\"flipV\":" + cfg.flipV + ",\"showSecs\":" + cfg.showSecs +
               ",\"hasPassword\":" + (apiHasPassword() ? "true" : "false") + ",\"events\":[";
    bool first = true;
    for (int i = 0; i < MAX_EVENTS; i++) {
        const Event& e = cfg.events[i];
        if (!e.month) continue;
        if (!first) j += ',';
        first = false;
        j += String("{\"i\":") + i + ",\"m\":" + e.month + ",\"d\":" + e.day + ",\"a\":" + e.anim + ",\"t\":" + jsonStr(e.text) + "}";
    }
    return json(j + "]}");
}

// set  k=<setting> v=<value> [live=1 -> apply without writing flash]
static ApiResult opSet(const ApiArgs& a) {
    String k = a.get("k"), v = a.get("v");
    int n = v.toInt();
    auto flag = [&](uint8_t& f) { f = n ? 1 : 0; };

    if      (k == "br")          cfg.brightness = constrain(n, 0, 15);
    else if (k == "autoDim")     flag(cfg.autoDim);
    else if (k == "nightFrom")   cfg.nightFrom = constrain(n, 0, 23);
    else if (k == "nightTo")     cfg.nightTo = constrain(n, 0, 23);
    else if (k == "nightBr")     cfg.nightBr = constrain(n, 0, 16);
    else if (k == "fmt24")       flag(cfg.fmt24);
    else if (k == "leadingZero") flag(cfg.leadingZero);
    else if (k == "blinkColon")  flag(cfg.blinkColon);
    else if (k == "secondsBar")  flag(cfg.secondsBar);
    else if (k == "showDate")    flag(cfg.showDate);
    else if (k == "autoUpdate")  flag(cfg.autoUpdate);
    else if (k == "ldrOn")       flag(cfg.ldrOn);
    else if (k == "ldrInvert")   flag(cfg.ldrInvert);
    else if (k == "ldrMin")      cfg.ldrMin = constrain(n, 0, 15);
    else if (k == "ldrMax")      cfg.ldrMax = constrain(n, 0, 15);
    else if (k == "flipH")       flag(cfg.flipH);
    else if (k == "flipV")       flag(cfg.flipV);
    else if (k == "showSecs")    flag(cfg.showSecs);
    else if (k == "modules" || k == "hwType") {   // the display driver is set up at boot: restart to apply
        if (k == "modules") cfg.modules = constrain(n, (int)MIN_MODULES, (int)MAX_MODULES);
        else                cfg.hwType = constrain(n, 0, (int)MT_ICSTATION);
        settingsSave();
        scheduleRestart(1000);
        return ok("Restarting to apply");
    }
    else if (k == "roll")        { cfg.roll = constrain(n, 0, (int)ROLL_RANDOM); digitDemo = true; }
    else if (k == "hourlyAnim")  cfg.hourlyAnim = constrain(n, 0, (int)ANIM_RANDOM);
    else if (k == "bootAnim")    cfg.bootAnim = constrain(n, 0, (int)ANIM_RANDOM);
    else if (k == "tz") {
        if (!v.length() || v.length() >= sizeof(cfg.tz)) return fail(400, "Invalid time zone");
        strlcpy(cfg.tz, v.c_str(), sizeof(cfg.tz));
        setenv("TZ", cfg.tz, 1);
        tzset();
    } else {
        return fail(400, "Unknown setting");
    }
    if (!a.has("live")) settingsSave();
    applyBrightness(true);
    return ok();
}

static ApiResult opScan() {
    int n = WiFi.scanNetworks();
    String j = "[";
    for (int i = 0; i < n; i++) {
        String s = WiFi.SSID(i);
        if (!s.length()) continue;
        bool weakerDuplicate = false;   // mesh / dual-band routers list the same name several times
        for (int k = 0; k < n && !weakerDuplicate; k++)
            if (k != i && WiFi.SSID(k) == s && (WiFi.RSSI(k) > WiFi.RSSI(i) || (WiFi.RSSI(k) == WiFi.RSSI(i) && k < i)))
                weakerDuplicate = true;
        if (weakerDuplicate) continue;
        if (j.length() > 1) j += ',';
        j += String("{\"s\":") + jsonStr(s) + ",\"r\":" + WiFi.RSSI(i) + ",\"l\":" +
             (WiFi.encryptionType(i) == WIFI_AUTH_OPEN ? "0" : "1") + "}";
    }
    WiFi.scanDelete();
    return json(j + "]");
}

static ApiResult opWifi(const ApiArgs& a) {
    String s = a.get("ssid"), p = a.get("pass");
    if (!s.length() || s.length() > 32) return fail(400, "Enter the network name");
    if (p.length() > 64)                return fail(400, "Password is too long");
    strlcpy(cfg.ssid, s.c_str(), sizeof(cfg.ssid));
    strlcpy(cfg.pass, p.c_str(), sizeof(cfg.pass));
    settingsSave();
    scheduleRestart(1500);
    return ok();
}

// message  t=<text> every=<minutes, 0 = off> [show=1 -> scroll it now]
static ApiResult opMessage(const ApiArgs& a) {
    String t = a.get("t");
    t.trim();
    if (t.length() >= sizeof(cfg.msg)) return fail(400, "Message is too long");
    strlcpy(cfg.msg, t.c_str(), sizeof(cfg.msg));
    int every = a.get("every").toInt();
    cfg.msgEvery = (every == 1 || every == 5 || every == 15 || every == 30 || every == 60) ? every : 0;
    settingsSave();
    if (a.get("show") == "1" && cfg.msg[0]) scrollRequest = cfg.msg;
    return ok();
}

// event/add  m=<1..12> d=<1..31> a=<Anim> t=<text>
static ApiResult opEventAdd(const ApiArgs& a) {
    int m = a.get("m").toInt(), d = a.get("d").toInt(), an = a.get("a").toInt();
    String t = a.get("t");
    t.trim();
    static const uint8_t DAYS[12] = {31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    if (m < 1 || m > 12 || d < 1 || d > DAYS[m - 1]) return fail(400, "Invalid date");
    if (!t.length() || t.length() > 40)               return fail(400, "Text must be 1 to 40 characters");
    for (Event& e : cfg.events) {
        if (e.month) continue;
        e.month = m;
        e.day = d;
        e.anim = constrain(an, 0, (int)ANIM_RANDOM);
        strlcpy(e.text, t.c_str(), sizeof(e.text));
        settingsSave();
        return ok();
    }
    return fail(400, "All 8 special days are used - delete one first");
}

static ApiResult opEventDelete(const ApiArgs& a) {
    int i = a.get("i").toInt();
    if (i < 0 || i >= MAX_EVENTS) return fail(400, "Invalid entry");
    memset(&cfg.events[i], 0, sizeof(Event));
    settingsSave();
    return ok();
}

static ApiResult opEventShow(const ApiArgs& a) {
    int i = a.get("i").toInt();
    if (i < 0 || i >= MAX_EVENTS || !cfg.events[i].month) return fail(400, "Invalid entry");
    if (cfg.events[i].anim) animRequest = cfg.events[i].anim;
    scrollRequest = cfg.events[i].text;
    return ok();
}

// password  cur=<current> new=<new password, empty = remove the password>
static ApiResult opPassword(const ApiArgs& a) {
    if (apiHasPassword()) {
        uint8_t h[32];
        apiHashPassword(a.get("cur"), cfg.adminSalt, h);
        if (!apiSameBytes(h, cfg.adminHash, 32)) {
            delay(400);
            return fail(403, "Current password is wrong");
        }
    }
    String pw = a.get("new");
    if (!pw.length()) {
        memset(cfg.adminHash, 0, sizeof(cfg.adminHash));
        settingsSave();
        return ok("Removed");
    }
    if (pw.length() < 6 || pw.length() > 64) return fail(400, "Use 6 to 64 characters");
    esp_fill_random(cfg.adminSalt, sizeof(cfg.adminSalt));
    esp_fill_random(cfg.sessionKey, sizeof(cfg.sessionKey));
    apiHashPassword(pw, cfg.adminSalt, cfg.adminHash);
    settingsSave();
    return ok("Set");
}

// =================================================================================

// Ops callable without being trusted (the transports decide who is trusted):
//   status always; scan/wifi in setup mode; ota/check, ota/install, restart in safe mode.
static bool openOp(const String& op) {
    if (op == "status") return true;
    if (appMode == MODE_SETUP && (op == "scan" || op == "wifi")) return true;
    if (appMode == MODE_SAFE && (op == "ota/check" || op == "ota/install" || op == "restart")) return true;
    return false;
}

ApiResult apiCall(const String& op, const ApiArgs& a, bool trusted) {
    if (!trusted && !openOp(op)) return fail(401, "Login required");

    if (op == "status")      return opStatus(trusted);
    if (op == "config")      return opConfig();
    if (op == "set")         return opSet(a);
    if (op == "scan")        return opScan();
    if (op == "wifi")        return opWifi(a);
    if (op == "message")     return opMessage(a);
    if (op == "event/add")   return opEventAdd(a);
    if (op == "event/del")   return opEventDelete(a);
    if (op == "event/show")  return opEventShow(a);
    if (op == "password")    return opPassword(a);
    if (op == "show")        { scrollRequest = String("IP ") + WiFi.localIP().toString(); return ok(); }
    if (op == "digits")      { digitDemo = true; return ok(); }
    if (op == "modules")     { moduleTest = true; return ok(); }
    if (op == "anim")        { animRequest = constrain(a.get("n").toInt(), 0, (int)ANIM_RANDOM); return ok(); }
    if (op == "sync")        { startNtp(); return ok(); }
    if (op == "ota/check")   { otaRequest = OTA_CHECK; return ok(); }
    if (op == "ota/install") { otaRequest = OTA_INSTALL; return ok(); }
    if (op == "restart")     { scheduleRestart(800); return ok(); }
    if (op == "factory")     { settingsDefaults(); settingsSave(); scheduleRestart(800); return ok(); }
    return fail(404, "Unknown operation");
}
