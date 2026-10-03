// DotGlow display test: MAX7219 wiring + power check, no display library.
//
// The MAX7219 is driven by hand (bit-banged, ~25 kHz) so long or poor jumper wires still work.
// Each round, announced on serial at 115200:
//   0. pin check (once): shorts of the three data pins to GND or to each other
//   1. "display test" register: every LED full on (works whatever the other registers hold)
//   2. WIRE ORDER SEARCH: the 6 possible orders of the three data wires are tried in turn.
//      For order N every module shows N lit columns. The order whose
//      bars look clean is the real wiring; serial says which pin is which for that order.
//   3. with the expected order: module numbers, rows, columns, brightness ramp
// A reset during step 1 (all LEDs on) points to the 5 V supply: the next boot reports "brownout".

#include <Arduino.h>
#include <esp_system.h>

#if CONFIG_IDF_TARGET_ESP32S3
static const int P[3] = {11, 10, 12};   // expected: DIN, CS, CLK
static const char* BOARD = "ESP32-S3 (expected DIN GPIO11, CS GPIO10, CLK GPIO12)";
#else
static const int P[3] = {23, 5, 18};
static const char* BOARD = "ESP32 DevKit (expected DIN D23, CS D5, CLK D18)";
#endif
static const int MODULES = 4;   // sending to more modules than exist is harmless

static int DIN = P[0], CS = P[1], CLK = P[2];

// ---- MAX7219 ----------------------------------------------------------------------------

static void shiftOut16(uint8_t reg, uint8_t val) {
    uint16_t w = (uint16_t)reg << 8 | val;
    for (int i = 15; i >= 0; i--) {
        digitalWrite(DIN, (w >> i) & 1);
        delayMicroseconds(20);
        digitalWrite(CLK, HIGH);
        delayMicroseconds(20);
        digitalWrite(CLK, LOW);
    }
}

static void all(uint8_t reg, uint8_t val) {
    digitalWrite(CS, LOW);
    delayMicroseconds(5);
    for (int m = 0; m < MODULES; m++) shiftOut16(reg, val);
    digitalWrite(CS, HIGH);
    delayMicroseconds(30);
}

// vals[0] goes to the module nearest the ESP32 (it is shifted out last).
static void each(uint8_t reg, const uint8_t* vals) {
    digitalWrite(CS, LOW);
    delayMicroseconds(5);
    for (int m = MODULES - 1; m >= 0; m--) shiftOut16(reg, vals[m]);
    digitalWrite(CS, HIGH);
    delayMicroseconds(30);
}

static void clearAll() { for (int r = 1; r <= 8; r++) all(r, 0); }

static void init7219(uint8_t intensity) {
    for (int k = 0; k < 2; k++) {   // twice: the first frame may land on a half-latched chip
        all(0x0F, 0);           // display test off
        all(0x09, 0);           // no BCD decode
        all(0x0B, 7);           // scan all 8 rows
        all(0x0A, intensity);   // brightness 0..15
        all(0x0C, 1);           // leave shutdown
    }
    clearAll();
}

static void usePins(int din, int cs, int clk) {
    DIN = din; CS = cs; CLK = clk;
    for (int p : {DIN, CS, CLK}) { pinMode(p, OUTPUT); digitalWrite(p, LOW); }
    digitalWrite(CS, HIGH);
}

// Order N lights N full columns on every module (counted from the left): easy to count,
// and obviously clean or garbled.
static void showBars(int n) {
    for (int r = 1; r <= 8; r++) all(r, (uint8_t)(0xFF << (8 - n)));
}

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
    bool ok = true;
    for (int p : P) pinMode(p, INPUT_PULLUP);
    delay(5);
    for (int i = 0; i < 3; i++)
        if (digitalRead(P[i]) == LOW) { Serial.printf("  !! GPIO%d reads LOW with pull-up: shorted to GND?\n", P[i]); ok = false; }
    for (int a = 0; a < 3; a++) {
        for (int p : P) pinMode(p, INPUT_PULLUP);
        pinMode(P[a], OUTPUT);
        digitalWrite(P[a], LOW);
        delay(2);
        for (int b = 0; b < 3; b++)
            if (b != a && digitalRead(P[b]) == LOW) { Serial.printf("  !! GPIO%d and GPIO%d are shorted together\n", P[a], P[b]); ok = false; }
    }
    Serial.println(ok ? "  pins OK: no shorts found" : "  -> fix the wiring above first");
}

// the 6 orders of (DIN, CS, CLK) over the three pins
static const int ORDERS[6][3] = {{0, 1, 2}, {0, 2, 1}, {1, 0, 2}, {1, 2, 0}, {2, 0, 1}, {2, 1, 0}};

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

    usePins(P[0], P[1], P[2]);
    Serial.println(F("[1] ALL LEDs ON (display-test register), 3 s: every LED should be fully lit"));
    all(0x0C, 1);
    all(0x0F, 1);
    delay(3000);
    all(0x0F, 0);

    Serial.println(F("[2] wire order search: watch for the number of bars that looks CLEAN"));
    for (int o = 0; o < 6; o++) {
        usePins(P[ORDERS[o][0]], P[ORDERS[o][1]], P[ORDERS[o][2]]);
        init7219(6);
        showBars(o + 1);
        Serial.printf("  order %d: %d bar(s)  ->  DIN on GPIO%d, CS on GPIO%d, CLK on GPIO%d%s\n", o + 1, o + 1,
                      DIN, CS, CLK, o == 0 ? "  (the expected wiring)" : "");
        delay(3000);
        all(0x0C, 0);   // blank between orders
        delay(400);
    }

    usePins(P[0], P[1], P[2]);
    init7219(8);
    Serial.println(F("[3] expected wiring: module numbers (1, 2, 3, 4 dots), rows, columns, brightness"));
    uint8_t v[MODULES];
    for (int m = 0; m < MODULES; m++) v[m] = (uint8_t)(0xFF << (7 - m));
    each(1, v);
    delay(3000);
    for (int r = 1; r <= 8; r++) { clearAll(); all(r, 0xFF); delay(200); }
    for (int c = 7; c >= 0; c--) { for (int r = 1; r <= 8; r++) all(r, 1 << c); delay(120); }
    for (int r = 1; r <= 8; r++) all(r, 0xFF);
    for (int i = 0; i <= 15; i++) { all(0x0A, i); delay(150); }
    clearAll();
    Serial.println(F("round done (repeats)."));
    delay(1500);
}
