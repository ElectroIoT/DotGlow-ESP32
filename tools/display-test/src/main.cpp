// DotGlow display test: MAX7219 wiring + power check, no display library.
//
// The MAX7219 is driven by hand (bit-banged, ~50 kHz) so long or poor jumper wires still work.
// Steps (repeated forever, each announced on serial at 115200):
//   0. pin check: shorts of DIN / CS / CLK to GND or to each other
//   1. "display test" register: every LED full on (works whatever the other registers hold)
//   2. module numbers: module 1 shows 1 dot, module 2 shows 2 dots ... (finds the chain order / IN side)
//   3. rows, then columns, then a brightness ramp 0..15
// A reset during step 1 (all LEDs on) points to the 5 V supply: the next boot reports "brownout".

#include <Arduino.h>
#include <esp_system.h>

#if CONFIG_IDF_TARGET_ESP32S3
static const int DIN = 11, CS = 10, CLK = 12;
static const char* BOARD = "ESP32-S3 (DIN GPIO11, CS GPIO10, CLK GPIO12)";
#else
static const int DIN = 23, CS = 5, CLK = 18;
static const char* BOARD = "ESP32 DevKit (DIN D23, CS D5, CLK D18)";
#endif
static const int MODULES = 4;   // sending to more modules than exist is harmless

// ---- MAX7219 ----------------------------------------------------------------------------

static void shiftOut16(uint8_t reg, uint8_t val) {
    uint16_t w = (uint16_t)reg << 8 | val;
    for (int i = 15; i >= 0; i--) {
        digitalWrite(DIN, (w >> i) & 1);
        delayMicroseconds(10);
        digitalWrite(CLK, HIGH);
        delayMicroseconds(10);
        digitalWrite(CLK, LOW);
    }
}

// Same register / value to every module in the chain.
static void all(uint8_t reg, uint8_t val) {
    digitalWrite(CS, LOW);
    for (int m = 0; m < MODULES; m++) shiftOut16(reg, val);
    digitalWrite(CS, HIGH);
    delayMicroseconds(20);
}

// Per-module values: vals[0] goes to the module nearest the ESP32 (it is shifted out last).
static void each(uint8_t reg, const uint8_t* vals) {
    digitalWrite(CS, LOW);
    for (int m = MODULES - 1; m >= 0; m--) shiftOut16(reg, vals[m]);
    digitalWrite(CS, HIGH);
    delayMicroseconds(20);
}

static void init7219(uint8_t intensity) {
    all(0x0F, 0);           // display test off
    all(0x09, 0);           // no BCD decode
    all(0x0B, 7);           // scan all 8 rows
    all(0x0A, intensity);   // brightness 0..15
    all(0x0C, 1);           // leave shutdown
    for (int r = 1; r <= 8; r++) all(r, 0);
}

static void clearAll() { for (int r = 1; r <= 8; r++) all(r, 0); }

// ---- checks -------------------------------------------------------------------------------

static const char* resetName(esp_reset_reason_t r) {
    switch (r) {
        case ESP_RST_POWERON:  return "power on";
        case ESP_RST_BROWNOUT: return "BROWNOUT (the 5 V supply dropped: use a stronger supply / shorter cable / external 5 V)";
        case ESP_RST_PANIC:    return "crash";
        case ESP_RST_SW:       return "software restart";
        case ESP_RST_EXT:      return "reset button / USB";
        default:               return "other";
    }
}

static void pinCheck() {
    struct P { int pin; const char* name; } pins[] = {{DIN, "DIN"}, {CS, "CS"}, {CLK, "CLK"}};
    bool ok = true;
    // pulled up and left alone, a pin that reads LOW is tied to GND
    for (auto& p : pins) pinMode(p.pin, INPUT_PULLUP);
    delay(5);
    for (auto& p : pins) {
        if (digitalRead(p.pin) == LOW) {
            Serial.printf("  !! %s (GPIO%d) reads LOW with pull-up: shorted to GND?\n", p.name, p.pin);
            ok = false;
        }
    }
    // drive one LOW, the others pulled up: a neighbour that follows it is shorted to it
    for (auto& a : pins) {
        for (auto& p : pins) pinMode(p.pin, INPUT_PULLUP);
        pinMode(a.pin, OUTPUT);
        digitalWrite(a.pin, LOW);
        delay(2);
        for (auto& b : pins) {
            if (&a == &b) continue;
            if (digitalRead(b.pin) == LOW) {
                Serial.printf("  !! %s and %s are connected to each other (short)\n", a.name, b.name);
                ok = false;
            }
        }
    }
    Serial.println(ok ? "  pins OK: no shorts found" : "  -> fix the wiring above first");
    for (auto& p : pins) { pinMode(p.pin, OUTPUT); digitalWrite(p.pin, LOW); }
    digitalWrite(CS, HIGH);
}

void setup() {
    Serial.begin(115200);
    delay(800);
    Serial.println();
    Serial.println(F("=== DotGlow display test ==="));
    Serial.printf("Board: %s\n", BOARD);
    Serial.printf("Last reset: %s\n", resetName(esp_reset_reason()));
    Serial.println(F("Display: VCC -> 5V/VIN, GND -> GND, wires on the IN side (pins marked DIN)."));
    Serial.println(F("[0] pin check"));
    pinCheck();
}

void loop() {
    static int round = 0;
    Serial.printf("\n--- round %d ---\n", ++round);

    Serial.println(F("[1] ALL LEDs ON (display-test register), 4 s: every LED should be fully lit"));
    all(0x0C, 1);
    all(0x0F, 1);
    delay(4000);
    all(0x0F, 0);

    init7219(8);
    Serial.println(F("[2] module numbers: module next to the ESP32 = 1 dot, next = 2 dots ..."));
    uint8_t v[MODULES];
    for (int m = 0; m < MODULES; m++) v[m] = (uint8_t)(0xFF << (7 - m)) & 0xFF;   // m+1 dots in a row
    clearAll();
    each(1, v);
    for (int m = 0; m < MODULES; m++) v[m] = 0xFF;   // and a full bottom row on each module
    each(8, v);
    delay(4000);

    Serial.println(F("[3] rows top to bottom"));
    for (int r = 1; r <= 8; r++) { clearAll(); all(r, 0xFF); delay(250); }
    Serial.println(F("[4] columns left to right"));
    for (int c = 7; c >= 0; c--) { for (int r = 1; r <= 8; r++) all(r, 1 << c); delay(150); }
    Serial.println(F("[5] brightness 0 -> 15"));
    for (int r = 1; r <= 8; r++) all(r, 0xFF);
    for (int i = 0; i <= 15; i++) { all(0x0A, i); delay(200); }
    clearAll();
    Serial.println(F("round done (repeats). Tell which steps you saw."));
    delay(1500);
}
