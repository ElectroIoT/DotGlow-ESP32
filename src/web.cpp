#include "web.h"
#include "api.h"
#include "app.h"
#include "config.h"
#include "display.h"
#include "settings.h"
#include "web_pages.h"
#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <Update.h>

static WebServer server(80);
static DNSServer dns;
static bool      dnsOn = false;

static void sendOk() {
    server.send(200, "text/plain", "OK");
}

static void sendResult(const ApiResult& r) {
    server.send(r.code, r.json ? "application/json" : "text/plain", r.body);
}

// ---- optional settings-page login ------------------------------------------------
// No password set (the default) = open page. With a password, the browser gets a
// session cookie after logging in; changing the password renews it (logs everyone out).
// Forgotten password: hold the BOOT button for 10 s.

static String sessionHex() {
    char hex[33];
    for (int i = 0; i < 16; i++) sprintf(hex + 2 * i, "%02x", cfg.sessionKey[i]);
    return hex;
}

static bool authed() {
    if (!apiHasPassword()) return true;
    String c = server.header("Cookie");
    int i = c.indexOf("mc_session=");
    if (i < 0) return false;
    String v = c.substring(i + 11, i + 11 + 32);
    String want = sessionHex();
    return v.length() == 32 && apiSameBytes((const uint8_t*)v.c_str(), (const uint8_t*)want.c_str(), 32);
}

static void setSessionCookie(bool valid) {
    server.sendHeader("Set-Cookie", valid ? "mc_session=" + sessionHex() + "; Path=/; Max-Age=31536000; HttpOnly; SameSite=Strict"
                                          : String("mc_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict"));
}

static uint8_t  loginFails = 0;
static uint32_t loginLockedUntil = 0;

static void handleLogin() {
    if (loginLockedUntil && (int32_t)(millis() - loginLockedUntil) < 0) {
        server.send(429, "text/plain", "Too many wrong passwords - wait a minute");
        return;
    }
    uint8_t h[32];
    apiHashPassword(server.arg("pw"), cfg.adminSalt, h);
    if (!apiHasPassword() || apiSameBytes(h, cfg.adminHash, 32)) {
        loginFails = 0;
        setSessionCookie(true);
        sendOk();
        return;
    }
    if (++loginFails >= 5) {
        loginFails = 0;
        loginLockedUntil = millis() + 60000;
    }
    delay(400);   // slows down guessing
    server.send(403, "text/plain", "Wrong password");
}

// ---- pages ---------------------------------------------------------------------

static void handleRoot() {
    const char* page = appMode == MODE_SETUP ? WIFI_HTML : appMode == MODE_SAFE ? SAFE_HTML
                     : authed() ? MAIN_HTML : LOGIN_HTML;
    server.send_P(200, "text/html", page);
}

// Captive portal: phones probe URLs like /generate_204 or /hotspot-detect.html;
// redirecting them to our page makes the "Sign in to network" screen pop up.
static void handleNotFound() {
    if (appMode == MODE_SETUP) {
        server.sendHeader("Location", "http://192.168.4.1/", true);
        server.send(302, "text/plain", "");
    } else {
        server.send(404, "text/plain", "Not found");
    }
}

// ---- API: /api/<op> -> apiCall(op) ---------------------------------------------------

static void handleApi(const String& op) {
    ApiArgs args;
    args.get = [](const char* k) { return server.arg(k); };
    args.has = [](const char* k) { return server.hasArg(k); };
    bool trusted = authed();
    ApiResult r = apiCall(op, args, trusted);
    if (op == "password" && r.code == 200) setSessionCookie(r.body == "Set");   // new password: stay logged in
    sendResult(r);
}

static void api(const char* uri, HTTPMethod method) {
    String op = String(uri).substring(5);   // "/api/event/add" -> "event/add"
    server.on(uri, method, [op]() { handleApi(op); });
}

// ---- manual firmware upload (password protected) ----------------------------------------

static bool passwordOk(const String& pass) {
    if (!pass.length()) return false;
    uint8_t h[32];
    apiSha256((const uint8_t*)pass.c_str(), pass.length(), nullptr, 0, h);
    char hex[65];
    for (int i = 0; i < 32; i++) sprintf(hex + 2 * i, "%02x", h[i]);
    return strcasecmp(hex, UPDATE_PASS_SHA256) == 0;
}

static String  uploadError;
static bool    uploadAuthed = false;
static uint8_t pinFailures = 0;

static void handleUploadDone() {
    bool ok = uploadAuthed && !uploadError.length() && !Update.hasError();
    if (!ok && !uploadError.length()) uploadError = "Update failed";
    server.send(ok ? 200 : 400, "text/plain", ok ? "OK" : uploadError);
    if (ok) {
        scrollRequest = "";
        scheduleRestart(1000);
    }
}

static void handleUploadChunk() {
    HTTPUpload& up = server.upload();
    if (up.status == UPLOAD_FILE_START) {
        uploadError = "";
        uploadAuthed = false;
        if (!strlen(UPDATE_PASS_SHA256))    { uploadError = "Upload is disabled in this firmware"; return; }
        if (pinFailures >= 5)               { uploadError = "Too many wrong passwords - restart the clock to try again"; return; }
        if (!passwordOk(server.header("X-Pin"))) {
            pinFailures++;
            uploadError = "Wrong update password";
            return;
        }
        pinFailures = 0;
        uploadAuthed = true;
        fbClear();
        drawText(1, "Update");
        fbShow();
        if (!Update.begin(UPDATE_SIZE_UNKNOWN)) uploadError = "Cannot start update: " + String(Update.errorString());
    } else if (up.status == UPLOAD_FILE_WRITE) {
        if (uploadAuthed && !uploadError.length() && Update.write(up.buf, up.currentSize) != up.currentSize)
            uploadError = "Write failed: " + String(Update.errorString());
    } else if (up.status == UPLOAD_FILE_END) {
        if (uploadAuthed && !uploadError.length() && !Update.end(true))
            uploadError = "Invalid firmware: " + String(Update.errorString());
    } else if (up.status == UPLOAD_FILE_ABORTED) {
        if (uploadAuthed) Update.abort();
        uploadError = "Upload aborted";
    }
}

// ---- setup -----------------------------------------------------------------------

void webBegin() {
    // pages
    server.on("/", HTTP_GET, handleRoot);   // serves the login page itself when needed
    server.on("/login", HTTP_GET, []() { server.send_P(200, "text/html", LOGIN_HTML); });
    server.on("/style.css", HTTP_GET, []() {
        server.sendHeader("Cache-Control", "max-age=86400");
        server.send_P(200, "text/css", STYLE_CSS);
    });
    server.on("/wifi", HTTP_GET, []() {
        if (appMode != MODE_SETUP && !authed()) { server.sendHeader("Location", "/login"); server.send(302); return; }
        server.send_P(200, "text/html", WIFI_HTML);
    });
    server.on("/update", HTTP_GET, []() { server.send_P(200, "text/html", UPDATE_HTML); });

    // login + firmware upload (web only)
    server.on("/api/login", HTTP_POST, handleLogin);
    server.on("/api/logout", HTTP_POST, []() { setSessionCookie(false); sendOk(); });
    server.on("/api/update", HTTP_POST, handleUploadDone, handleUploadChunk);   // has its own update password

    // everything else: shared with the app (api.cpp decides what needs login)
    api("/api/status", HTTP_GET);
    api("/api/config", HTTP_GET);
    api("/api/scan", HTTP_GET);
    for (const char* uri : {"/api/set", "/api/wifi", "/api/message", "/api/event/add", "/api/event/del",
                            "/api/event/show", "/api/password", "/api/show", "/api/digits", "/api/modules",
                            "/api/anim", "/api/sync", "/api/ota/check", "/api/ota/install", "/api/restart",
                            "/api/factory"})
        api(uri, HTTP_POST);

    server.onNotFound(handleNotFound);
    static const char* headers[] = {"X-Pin", "Cookie"};   // update password, login session
    server.collectHeaders(headers, 2);
    server.begin();
}

void webStartPortal() {
    dns.setErrorReplyCode(DNSReplyCode::NoError);
    dns.start(53, "*", WiFi.softAPIP());
    dnsOn = true;
}

void webPause(bool pause) {
    if (pause) server.stop();
    else       server.begin();
}

void webLoop() {
    if (dnsOn) dns.processNextRequest();
    server.handleClient();
}
