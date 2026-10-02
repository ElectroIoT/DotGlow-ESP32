// Commands shared by the web page (HTTP) and the app (Bluetooth): one implementation,
// two transports. See docs/PROTOCOL.md for the list of operations.
#pragma once

#include <Arduino.h>
#include <functional>

// Named string arguments of a command (form fields over HTTP, a JSON object over BLE).
struct ApiArgs {
    std::function<String(const char*)> get;   // "" when missing
    std::function<bool(const char*)>   has;
};

struct ApiResult {
    int    code = 200;                // HTTP-style status: 200 ok, 400 bad request, 401, 403, 404, 429
    String body = "OK";
    bool   json = false;              // body is a JSON document (else plain text)
};

// trusted: the caller is the owner (logged in on the web page, or a paired phone).
ApiResult apiCall(const String& op, const ApiArgs& args, bool trusted);

String jsonStr(const String& s);      // quoted + escaped JSON string
bool   apiHasPassword();              // a settings password is set
void   apiHashPassword(const String& pw, const uint8_t salt[16], uint8_t out[32]);
bool   apiSameBytes(const uint8_t* a, const uint8_t* b, size_t n);   // constant time
void   apiSha256(const uint8_t* a, size_t na, const uint8_t* b, size_t nb, uint8_t out[32]);
