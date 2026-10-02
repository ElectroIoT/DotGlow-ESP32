#include "ota.h"
#include "config.h"
#include "display.h"
#include "github_roots.h"
#include "safemode.h"
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <HTTPUpdate.h>
#include <time.h>

// "latest" always points at the newest full release; GitHub redirects it to the asset download.
static const char* URL_BASE = "https://github.com/" GITHUB_REPO "/releases/latest/download/";

OtaState ota;

// Every connection verifies the server certificate against the roots in github_roots.h,
// so only files really served by GitHub for this repo can be installed.
static void secure(WiFiClientSecure& client) {
    client.setCACert(GITHUB_ROOTS);
    client.setTimeout(15);   // seconds
}

static bool ready() {
    if (WiFi.status() != WL_CONNECTED) {
        ota.message = "No WiFi";
        return false;
    }
    if (time(nullptr) < 1600000000) {
        ota.message = "Waiting for internet time";
        return false;
    }
    return true;
}

static void parseVersion(const String& v, int out[3]) {
    out[0] = out[1] = out[2] = 0;
    int part = 0;
    for (size_t i = 0; i < v.length() && part < 3; i++) {
        char c = v[i];
        if (c >= '0' && c <= '9') out[part] = out[part] * 10 + (c - '0');
        else if (c == '.') part++;
    }
}

bool otaNewer(const String& v) {
    int a[3], b[3];
    parseVersion(v, a);
    parseVersion(FW_VERSION, b);
    for (int i = 0; i < 3; i++)
        if (a[i] != b[i]) return a[i] > b[i];
    return false;
}

bool otaCheck() {
    ota.checkedAt = millis() | 1;
    if (!ready()) return false;

    WiFiClientSecure client;
    secure(client);
    HTTPClient http;
    http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);
    http.setTimeout(15000);
    if (!http.begin(client, String(URL_BASE) + "version.txt")) {
        ota.message = "Could not reach GitHub";
        ota.retry = true;
        return false;
    }
    int code = http.GET();
    if (code != HTTP_CODE_OK) {
        if (code == HTTP_CODE_NOT_FOUND) {
            ota.message = "No release published yet";
        } else {
            ota.message = "Could not reach GitHub (" + HTTPClient::errorToString(code) + ")";
            ota.retry = true;
        }
        http.end();
        Serial.println("OTA: " + ota.message);
        return false;
    }
    String v = http.getString();
    http.end();
    v.trim();
    if (v.startsWith("v") || v.startsWith("V")) v.remove(0, 1);
    if (!v.length() || v.length() > 16) {
        ota.message = "Bad version.txt in release";
        return false;
    }
    ota.latest = v;
    ota.retry = false;
    bool newer = otaNewer(v);
    ota.message = newer ? "Version " + v + " is available" : String("Up to date");
    Serial.printf("Update check: latest %s, running %s\n", v.c_str(), FW_VERSION);
    return newer;
}

void otaInstall() {
    if (!ready()) return;
    Serial.println(F("Installing update from GitHub"));
    fbClear();
    drawText(1, "Update");
    fbShow();

    WiFiClientSecure client;
    secure(client);
    httpUpdate.setFollowRedirects(HTTPC_FORCE_FOLLOW_REDIRECTS);
    httpUpdate.rebootOnUpdate(false);
    httpUpdate.setLedPin(-1);
    httpUpdate.onProgress([](int done, int total) {   // progress bar across the display
        if (total <= 0) return;
        fbClear();
        int len = (int64_t)done * W / total;
        for (int x = 0; x < len; x++)
            for (int y = 2; y < 6; y++) fbSet(x, y, true);
        for (int x = 0; x < W; x++) { fbSet(x, 0, true); fbSet(x, 7, true); }
        fbShow();
    });

    t_httpUpdate_return r = httpUpdate.update(client, String(URL_BASE) + FIRMWARE_ASSET);
    if (r == HTTP_UPDATE_OK) {
        Serial.println(F("Update OK, restarting"));
        scrollText("Updated!");
        restart();
    }
    ota.message = "Update failed: " + httpUpdate.getLastErrorString();
    ota.retry = true;
    Serial.println(ota.message);
    scrollText("Update failed");
}
