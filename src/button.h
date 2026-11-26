// A push button from a pin to GND (internal pull-up): debounced taps and holds.
#pragma once

#include <Arduino.h>

struct Button {
    enum Event : uint8_t { NONE, TAP, HOLD };
    static const uint32_t DEBOUNCE_MS = 30, HOLD_MS = 1200;

    explicit Button(uint8_t p) : pin(p) {}
    void begin() { pinMode(pin, INPUT_PULLUP); }

    // TAP when released early; HOLD once, while still down, after HOLD_MS.
    Event poll() {
        const bool pressed = digitalRead(pin) == LOW;
        if (pressed != down && millis() - changedAt > DEBOUNCE_MS) {
            changedAt = millis();
            down = pressed;
            if (down) {
                downAt = millis();
                held = false;
            } else if (!held) {
                return TAP;
            }
        }
        if (down && !held && millis() - downAt >= HOLD_MS) {
            held = true;
            return HOLD;
        }
        return NONE;
    }

private:
    uint8_t  pin;
    bool     down = false, held = false;
    uint32_t downAt = 0, changedAt = 0;
};
