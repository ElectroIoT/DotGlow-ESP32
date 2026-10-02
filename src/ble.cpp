#include "ble.h"
#include "api.h"
#include "app.h"
#include "config.h"
#include <ArduinoJson.h>
#include <NimBLEDevice.h>
#include <Update.h>
#include <esp_random.h>
#include <map>
#include <vector>

// ---- GATT layout (keep in sync with docs/PROTOCOL.md and the app) -----------------
static const char* SERVICE_UUID = "6f4a0001-1d2c-4a8e-9c3d-2b7e5f9a1c00";
static const char* INFO_UUID    = "6f4a0002-1d2c-4a8e-9c3d-2b7e5f9a1c00";   // read, open: who am I
static const char* RX_UUID      = "6f4a0003-1d2c-4a8e-9c3d-2b7e5f9a1c00";   // write, paired only: requests
static const char* TX_UUID      = "6f4a0004-1d2c-4a8e-9c3d-2b7e5f9a1c00";   // notify, paired only: responses
static const char* OTA_UUID     = "6f4a0005-1d2c-4a8e-9c3d-2b7e5f9a1c00";   // write, paired only: firmware bytes
static const int   PROTO_VERSION = 1;
static const uint32_t PASSKEY_SHOW_MS = 60000;

static NimBLEServer*         server = nullptr;
static String                devName;
static NimBLECharacteristic* txChar = nullptr;
static uint16_t              connHandle = BLE_HS_CONN_HANDLE_NONE;

// Requests arrive in the BLE host task; they are run in the main loop, one at a time,
// because some operations block (WiFi scan) or touch the display.
static SemaphoreHandle_t   lock;
static String              rxBuffer;
static std::vector<String> requests;

static volatile uint32_t shownPasskey = 0;
static volatile uint32_t passkeyUntil = 0;

// Firmware update over Bluetooth: "ota/begin", then the raw image written to OTA_UUID,
// then "ota/end". The bytes go straight to flash in the BLE host task; the phone writes
// with response, so it can never get ahead of the flash.
static volatile bool     otaActive  = false;
static volatile uint32_t otaSize    = 0;
static volatile uint32_t otaWritten = 0;
static String            otaError;   // set by the host task, read by the main loop (under lock)

static void otaStop(const String& why) {
    if (otaActive) Update.abort();
    otaActive = false;
    if (why.length()) {
        xSemaphoreTake(lock, portMAX_DELAY);
        otaError = why;
        xSemaphoreGive(lock);
        Serial.println("BLE update stopped: " + why);
    }
}

// =================================================================================
// Callbacks (BLE host task)
// =================================================================================

class ServerCallbacks : public NimBLEServerCallbacks {
    // Several links may be open at once (a reopened app while the old link times out,
    // the phone's own system services...), so the clock keeps advertising while connected:
    // a stale connection must never lock the app out. Responses go to the newest link.
    void onConnect(NimBLEServer* s, ble_gap_conn_desc* desc) override {
        connHandle = desc->conn_handle;
        Serial.printf("BLE: phone connected (%u open)\n", s->getConnectedCount());
        if (s->getConnectedCount() < CONFIG_BT_NIMBLE_MAX_CONNECTIONS) NimBLEDevice::startAdvertising();
    }

    void onDisconnect(NimBLEServer* s, ble_gap_conn_desc* desc) override {
        if (desc->conn_handle == connHandle) {
            connHandle = BLE_HS_CONN_HANDLE_NONE;
            passkeyUntil = 0;
            xSemaphoreTake(lock, portMAX_DELAY);
            rxBuffer = "";
            xSemaphoreGive(lock);
            if (otaActive) otaStop("Phone disconnected");
        }
        Serial.println(F("BLE: phone disconnected"));
        NimBLEDevice::startAdvertising();
    }

    // Display-only pairing: the clock makes up a PIN and shows it on the LEDs;
    // the user types it into the phone's pairing dialog.
    uint32_t onPassKeyRequest() override {
        uint32_t pk = esp_random() % 1000000;
        shownPasskey = pk;
        passkeyUntil = (millis() + PASSKEY_SHOW_MS) | 1;
#ifdef PIN_TO_SERIAL   // test builds only (env:esp32s3_test): lets a developer pair without the display
        Serial.printf("BLE: pairing PIN %06u (test build)\n", (unsigned)pk);
#else
        Serial.println(F("BLE: pairing, PIN on the display"));
#endif
        return pk;
    }

    void onAuthenticationComplete(ble_gap_conn_desc* desc) override {
        passkeyUntil = 0;
        if (!desc->sec_state.encrypted || !desc->sec_state.authenticated) {
            Serial.println(F("BLE: pairing failed"));
            NimBLEDevice::getServer()->disconnect(desc->conn_handle);
            return;
        }
        Serial.println(F("BLE: paired / encrypted"));
        if (desc->sec_state.bonded) scrollRequest = "Phone paired";
    }
};

class RxCallbacks : public NimBLECharacteristicCallbacks {
    void onWrite(NimBLECharacteristic* c) override {
        std::string v = c->getValue();
        xSemaphoreTake(lock, portMAX_DELAY);
        rxBuffer += String(v.c_str()).substring(0, v.size());
        int nl;
        while ((nl = rxBuffer.indexOf('\n')) >= 0) {   // one request per line
            if (requests.size() < 8) requests.push_back(rxBuffer.substring(0, nl));
            rxBuffer.remove(0, nl + 1);
        }
        if (rxBuffer.length() > 2048) rxBuffer = "";   // runaway line: drop it
        xSemaphoreGive(lock);
    }
};

class OtaCallbacks : public NimBLECharacteristicCallbacks {
    void onWrite(NimBLECharacteristic* c) override {
        if (!otaActive) return;
        std::string v = c->getValue();
        if (otaWritten + v.size() > otaSize) { otaStop("More data than announced"); return; }
        if (Update.write((uint8_t*)v.data(), v.size()) != v.size()) {
            otaStop(String("Write failed: ") + Update.errorString());
            return;
        }
        otaWritten = otaWritten + v.size();
    }
};

// =================================================================================
// Main-loop side
// =================================================================================

static void send(const String& line) {
    if (!txChar || connHandle == BLE_HS_CONN_HANDLE_NONE) return;
    String msg = line + "\n";
    size_t chunk = server->getPeerMTU(connHandle);
    chunk = chunk > 3 ? chunk - 3 : 20;   // ATT header
    for (size_t i = 0; i < msg.length(); i += chunk) {
        String part = msg.substring(i, i + chunk);
        txChar->setValue((const uint8_t*)part.c_str(), part.length());
        txChar->notify();
        delay(4);   // let the stack drain between notifications
    }
}

// "asset" is the GitHub release file this clock runs; "ota" = updates over Bluetooth supported
static String infoJson() {
    return String("{\"name\":") + jsonStr(devName) + ",\"fw\":" + jsonStr(FW_VERSION) +
           ",\"board\":" + jsonStr(BOARD_NAME) + ",\"asset\":" + jsonStr(FIRMWARE_ASSET) +
           ",\"proto\":" + PROTO_VERSION + ",\"ota\":1}";
}

static void handle(const String& line) {
    JsonDocument req;
    if (deserializeJson(req, line)) {
        send("{\"id\":0,\"code\":400,\"body\":\"Bad JSON\"}");
        return;
    }
    long id = req["id"] | 0L;
    String op = req["op"] | "";
    std::map<String, String> args;
    for (JsonPair kv : req["args"].as<JsonObject>()) args[kv.key().c_str()] = kv.value().as<String>();

    ApiResult r;
    if (op == "info") {
        r.json = true;
        r.body = infoJson();
    } else if (op == "ota/begin") {
        uint32_t size = args["size"].toInt();
        String md5 = args["md5"];
        otaStop("");
        if (Update.isRunning()) {
            r.code = 409; r.body = "Another update is running";
        } else if (!size || !Update.begin(size, U_FLASH)) {
            r.code = 400; r.body = String("Cannot start update: ") + Update.errorString();
        } else if (md5.length() && !Update.setMD5(md5.c_str())) {
            Update.abort();
            r.code = 400; r.body = "Bad MD5";
        } else {
            otaSize = size;
            otaWritten = 0;
            xSemaphoreTake(lock, portMAX_DELAY);
            otaError = "";
            xSemaphoreGive(lock);
            otaActive = true;
            uint16_t mtu = server->getPeerMTU(connHandle);
            r.json = true;
            r.body = String("{\"chunk\":") + min(512, mtu > 3 ? mtu - 3 : 20) + "}";
            Serial.printf("BLE update: receiving %u bytes\n", (unsigned)size);
        }
    } else if (op == "ota/status") {
        xSemaphoreTake(lock, portMAX_DELAY);
        String err = otaError;
        xSemaphoreGive(lock);
        r.json = true;
        r.body = String("{\"active\":") + (otaActive ? "true" : "false") + ",\"written\":" + (uint32_t)otaWritten +
                 ",\"size\":" + (uint32_t)otaSize + ",\"error\":" + jsonStr(err) + "}";
    } else if (op == "ota/end") {
        xSemaphoreTake(lock, portMAX_DELAY);
        String err = otaError;
        xSemaphoreGive(lock);
        if (!otaActive) {
            r.code = 400; r.body = err.length() ? err : String("No update running");
        } else if (otaWritten != otaSize) {
            r.code = 400; r.body = String("Only ") + (uint32_t)otaWritten + " of " + (uint32_t)otaSize + " bytes arrived";
            otaStop(r.body);
        } else {
            otaActive = false;
            if (!Update.end()) {
                r.code = 400; r.body = String("Invalid firmware: ") + Update.errorString();
            } else {
                r.body = "OK";
                Serial.println(F("BLE update: done, restarting"));
                scheduleRestart(1500);
            }
        }
    } else if (op == "ota/abort") {
        otaStop("Cancelled");
        r.body = "OK";
    } else if (op == "phones/forget") {
        send(String("{\"id\":") + id + ",\"code\":200,\"body\":\"OK\"}");
        delay(200);
        bleForgetPhones();
        return;
    } else {
        if (op == "factory") bleForgetPhones();
        ApiArgs a;
        a.get = [&args](const char* k) { auto it = args.find(k); return it == args.end() ? String() : it->second; };
        a.has = [&args](const char* k) { return args.count(k) > 0; };
        r = apiCall(op, a, true);   // only paired, encrypted phones can write requests
    }
    send(String("{\"id\":") + id + ",\"code\":" + r.code + ",\"body\":" + (r.json ? r.body : jsonStr(r.body)) + "}");
}

void bleLoop() {
    while (true) {
        String next;
        xSemaphoreTake(lock, portMAX_DELAY);
        if (!requests.empty()) {
            next = requests.front();
            requests.erase(requests.begin());
        }
        xSemaphoreGive(lock);
        if (!next.length()) return;
        handle(next);
    }
}

bool bleUpdateProgress(uint8_t& percent) {
    if (!otaActive || !otaSize) return false;
    percent = (uint64_t)otaWritten * 100 / otaSize;
    return true;
}

bool blePasskey(uint32_t& passkey) {
    if (!passkeyUntil || (int32_t)(millis() - passkeyUntil) >= 0) return false;
    passkey = shownPasskey;
    return true;
}

void bleForgetPhones() {
    NimBLEDevice::deleteAllBonds();
    if (connHandle != BLE_HS_CONN_HANDLE_NONE) server->disconnect(connHandle);
    Serial.println(F("BLE: all paired phones removed"));
}

void bleBegin(const String& name) {
    lock = xSemaphoreCreateMutex();
    devName = name;
    NimBLEDevice::init(name.c_str());
    NimBLEDevice::setPower(ESP_PWR_LVL_P9);
    NimBLEDevice::setMTU(517);
    NimBLEDevice::setSecurityAuth(true, true, true);          // bonding, MITM protection, LE Secure Connections
    NimBLEDevice::setSecurityIOCap(BLE_HS_IO_DISPLAY_ONLY);   // the clock shows the PIN

    server = NimBLEDevice::createServer();
    server->setCallbacks(new ServerCallbacks());
    NimBLEService* svc = server->createService(SERVICE_UUID);

    NimBLECharacteristic* info = svc->createCharacteristic(INFO_UUID, NIMBLE_PROPERTY::READ);
    info->setValue(infoJson());

    NimBLECharacteristic* rx = svc->createCharacteristic(
        RX_UUID, NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_NR | NIMBLE_PROPERTY::WRITE_ENC | NIMBLE_PROPERTY::WRITE_AUTHEN);
    rx->setCallbacks(new RxCallbacks());

    NimBLECharacteristic* otaChar = svc->createCharacteristic(
        OTA_UUID, NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_ENC | NIMBLE_PROPERTY::WRITE_AUTHEN, 512);
    otaChar->setCallbacks(new OtaCallbacks());

    txChar = svc->createCharacteristic(
        TX_UUID, NIMBLE_PROPERTY::NOTIFY | NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::READ_ENC | NIMBLE_PROPERTY::READ_AUTHEN);

    svc->start();
    NimBLEAdvertising* adv = NimBLEDevice::getAdvertising();
    adv->addServiceUUID(SERVICE_UUID);
    adv->setScanResponse(true);   // the name goes in the scan response
    adv->start();
    Serial.printf("BLE: advertising as \"%s\"\n", name.c_str());
}
