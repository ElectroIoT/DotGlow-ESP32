#include "sound.h"
#include "config.h"
#include "settings.h"
#include <driver/i2s.h>
#include <math.h>

// =================================================================================
// Sounds as note lists. All tunes are original.
// =================================================================================

enum Wave : uint8_t {
    W_SINE,      // pure tone
    W_SQUARE,    // buzzy (a clipped sine, softer than a true square)
    W_BELL,      // inharmonic partials, long decay
    W_WOOD       // marimba-like knock, short decay
};

struct Note {
    uint16_t freq;   // Hz at the start, 0 = rest
    uint16_t end;    // Hz at the end (a glide), 0 = stays on freq
    uint16_t ms;
    Wave     wave;
};

#define N(f, ms, w)      {f, 0, ms, w}
#define GLIDE(a, b, ms)  {a, b, ms, W_SINE}
#define REST(ms)         {0, 0, ms, W_SINE}

// A sound that rings is repeated, so each one ends in the pause before the next round.
static const Note BEEP[] = {N(2000, 90, W_SQUARE), REST(70), N(2000, 90, W_SQUARE), REST(70), N(2000, 90, W_SQUARE),
                            REST(70), N(2000, 90, W_SQUARE), REST(550)};
static const Note DIGITAL[] = {N(2637, 60, W_SQUARE), REST(50), N(2637, 60, W_SQUARE), REST(330),
                               N(2637, 60, W_SQUARE), REST(50), N(2637, 60, W_SQUARE), REST(530)};
static const Note CHIME[] = {N(988, 550, W_BELL), N(784, 900, W_BELL), REST(500)};
static const Note BELL[] = {N(1175, 480, W_BELL), N(1175, 480, W_BELL), N(1175, 900, W_BELL), REST(400)};
static const Note RISE[] = {N(523, 150, W_SINE), N(659, 150, W_SINE), N(784, 150, W_SINE), N(1047, 150, W_SINE),
                            N(1319, 150, W_SINE), N(1568, 420, W_BELL), REST(600)};
static const Note MARIMBA[] = {N(784, 170, W_WOOD), N(988, 170, W_WOOD), N(1175, 170, W_WOOD), N(988, 170, W_WOOD),
                               N(880, 170, W_WOOD), N(1319, 170, W_WOOD), N(1175, 340, W_WOOD), REST(650)};
static const Note BIRDS[] = {GLIDE(2600, 3900, 90), REST(40), GLIDE(2600, 3900, 90), REST(180), GLIDE(3600, 2500, 160),
                             REST(90), GLIDE(3000, 4200, 70), REST(30), GLIDE(3000, 4200, 70), REST(30),
                             GLIDE(3000, 4200, 70), REST(700)};
static const Note ARCADE[] = {N(660, 80, W_SQUARE), N(880, 80, W_SQUARE), N(1320, 80, W_SQUARE), REST(60),
                              N(990, 80, W_SQUARE), N(1320, 80, W_SQUARE), N(1760, 200, W_SQUARE), REST(500)};
static const Note SIREN[] = {GLIDE(600, 1500, 450), GLIDE(1500, 600, 450), GLIDE(600, 1500, 450),
                             GLIDE(1500, 600, 450), REST(150)};
static const Note PULSE[] = {N(440, 260, W_SINE), REST(240), N(440, 260, W_SINE), REST(1000)};

struct Tune {
    const char* name;
    const Note* notes;
    uint8_t     count;
};
#define TUNE(name, a) {name, a, sizeof(a) / sizeof(a[0])}
static const Tune TUNES[SND_COUNT] = {
    TUNE("Beep", BEEP),       TUNE("Digital watch", DIGITAL), TUNE("Door chime", CHIME), TUNE("Bell", BELL),
    TUNE("Sunrise", RISE),    TUNE("Marimba", MARIMBA),       TUNE("Birds", BIRDS),      TUNE("Arcade", ARCADE),
    TUNE("Siren", SIREN),     TUNE("Soft pulse", PULSE),
};

// Stopwatch cues: [style - 1][cue]. The closing rest spaces them out in the preview.
static const Note B_START[] = {N(1760, 90, W_SINE), REST(400)};
static const Note B_PAUSE[] = {N(1175, 70, W_SINE), REST(40), N(1175, 70, W_SINE), REST(400)};
static const Note B_RESET[] = {N(880, 220, W_SINE), REST(100)};
static const Note C_START[] = {N(3200, 14, W_WOOD), REST(400)};
static const Note C_PAUSE[] = {N(2200, 14, W_WOOD), REST(60), N(2200, 14, W_WOOD), REST(400)};
static const Note C_RESET[] = {N(1500, 24, W_WOOD), REST(100)};
static const Note A_START[] = {N(660, 60, W_SQUARE), N(990, 60, W_SQUARE), N(1320, 90, W_SQUARE), REST(400)};
static const Note A_PAUSE[] = {N(990, 70, W_SQUARE), N(660, 110, W_SQUARE), REST(400)};
static const Note A_RESET[] = {GLIDE(1400, 300, 220), REST(100)};
static const Note S_START[] = {GLIDE(2300, 2900, 80), N(2900, 240, W_SQUARE), REST(400)};
static const Note S_PAUSE[] = {N(2900, 90, W_SQUARE), REST(50), N(2900, 90, W_SQUARE), REST(400)};
static const Note S_RESET[] = {GLIDE(2900, 2100, 260), REST(100)};

#define CUE(a) TUNE("", a)
static const Tune CUES[SWS_COUNT - 1][3] = {
    {CUE(B_START), CUE(B_PAUSE), CUE(B_RESET)},
    {CUE(C_START), CUE(C_PAUSE), CUE(C_RESET)},
    {CUE(A_START), CUE(A_PAUSE), CUE(A_RESET)},
    {CUE(S_START), CUE(S_PAUSE), CUE(S_RESET)},
};

const char* soundName(uint8_t id) {
    return id < SND_COUNT ? TUNES[id].name : "";
}

const char* swSoundName(uint8_t style) {
    static const char* NAMES[SWS_COUNT] = {"Off", "Beep", "Click", "Arcade", "Whistle"};
    return style < SWS_COUNT ? NAMES[style] : "";
}

// =================================================================================
// Player task
// =================================================================================

static const int      RATE = 22050;
static const int      BLOCK = 256;          // frames per write
static const int      TABLE = 512;          // sine table length (power of two)
static const float    FULL_SCALE = 24000;   // headroom: the amplifier clips near full scale on 5 V
static const uint32_t RAMP_MS = 20000;      // a ringing sound reaches the set volume after this long
static const i2s_port_t PORT = I2S_NUM_0;

struct Request {
    const Tune* tunes[3];   // played one after another
    uint8_t     count;
    bool        ring;
};

static TaskHandle_t      task = nullptr;
static portMUX_TYPE      mux = portMUX_INITIALIZER_UNLOCKED;
static Request           pending;
static volatile uint32_t wanted = 0;       // changes with every play / stop request
static volatile bool     playing = false;
static volatile bool     ringing = false;
static float             sine[TABLE];

static void request(const Request& r) {
    if (!task) return;
    portENTER_CRITICAL(&mux);
    pending = r;
    wanted++;
    playing = r.count > 0;
    ringing = r.ring;
    portEXIT_CRITICAL(&mux);
    xTaskNotifyGive(task);
}

static inline float osc(uint32_t phase) {
    return sine[phase >> 23];   // top 9 bits index the 512-entry table
}

// One note into the I2S stream. false: a newer request arrived, stop here.
static bool playNote(const Note& n, uint32_t mine, bool ring, uint32_t startedAt) {
    static int16_t buf[BLOCK * 2];
    const int total = (int32_t)n.ms * RATE / 1000;
    const int attack = RATE / 250;                                      // 4 ms: no clicks
    const int release = min(total / 4, RATE / 100);                     // up to 10 ms
    const float hz2inc = 4294967296.0f / RATE;
    // percussive waves die away over the note
    const float tau = n.wave == W_BELL ? n.ms * 0.42f : n.ms * 0.28f;   // ms
    const float decay = (n.wave == W_BELL || n.wave == W_WOOD) ? expf(-1000.0f / (max(tau, 3.0f) * RATE)) : 1.0f;
    float env = 1.0f;
    uint32_t p1 = 0, p2 = 0, p3 = 0;

    for (int done = 0; done < total;) {
        if (wanted != mine) return false;
        const int len = min(BLOCK, total - done);
        const float f = n.end ? n.freq + (float)(n.end - n.freq) * done / total : n.freq;
        const uint32_t inc = (uint32_t)(f * hz2inc);
        float gain = (float)cfg.volume / MAX_VOLUME;
        gain *= gain;   // loudness is heard roughly as the square
        if (ring) {
            uint32_t age = millis() - startedAt;
            if (age < RAMP_MS) gain *= 0.3f + 0.7f * age / RAMP_MS;
        }
        for (int i = 0; i < len; i++, done++) {
            float v = 0;
            if (n.freq) {
                switch (n.wave) {
                    case W_SQUARE: v = constrain(osc(p1) * 3.0f, -1.0f, 1.0f) * 0.7f; break;
                    case W_BELL:   v = 0.6f * osc(p1) + 0.25f * osc(p2) + 0.15f * osc(p3); break;
                    case W_WOOD:   v = 0.8f * osc(p1) + 0.2f * osc(p3); break;
                    default:       v = osc(p1); break;
                }
                p1 += inc;
                p2 += (uint32_t)(inc * 2.0f);
                p3 += n.wave == W_BELL ? (uint32_t)(inc * 2.76f) : inc * 4u;   // inharmonic = metallic
                if (done < attack) v *= (float)done / attack;
                if (release && done > total - release) v *= (float)(total - done) / release;
                v *= env;
                env *= decay;
            }
            const int16_t s = (int16_t)(v * gain * FULL_SCALE);
            buf[i * 2] = buf[i * 2 + 1] = s;
        }
        size_t written;
        i2s_write(PORT, buf, len * 4, &written, portMAX_DELAY);
    }
    return true;
}

static void soundTask(void*) {
    uint32_t seen = 0;
    for (;;) {
        if (wanted == seen) ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        if (wanted == seen) continue;
        portENTER_CRITICAL(&mux);
        const Request r = pending;
        seen = wanted;
        portEXIT_CRITICAL(&mux);

        if (r.count && cfg.volume) {
            digitalWrite(PIN_AMP_SD, HIGH);
            const uint32_t startedAt = millis();
            bool current = true;
            do {
                for (uint8_t t = 0; t < r.count && current; t++)
                    for (uint8_t k = 0; k < r.tunes[t]->count && current; k++)
                        current = playNote(r.tunes[t]->notes[k], seen, r.ring, startedAt);
            } while (current && r.ring);
        }
        portENTER_CRITICAL(&mux);
        const bool idle = wanted == seen;
        if (idle) playing = false;
        portEXIT_CRITICAL(&mux);
        if (idle) {
            vTaskDelay(pdMS_TO_TICKS(60));        // let the queued samples play out
            if (wanted == seen) {
                i2s_zero_dma_buffer(PORT);
                digitalWrite(PIN_AMP_SD, LOW);    // amplifier off: no idle hiss, no idle current
            }
        }
    }
}

void soundBegin() {
    pinMode(PIN_AMP_SD, OUTPUT);
    digitalWrite(PIN_AMP_SD, LOW);
    for (int i = 0; i < TABLE; i++) sine[i] = sinf(2.0f * (float)PI * i / TABLE);

    i2s_config_t c = {};
    c.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX);
    c.sample_rate = RATE;
    c.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;
    c.channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT;
    c.communication_format = I2S_COMM_FORMAT_STAND_I2S;
    c.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
    c.dma_buf_count = 4;
    c.dma_buf_len = BLOCK;
    c.tx_desc_auto_clear = true;   // silence, not a stuck buzz, if the task falls behind
    i2s_pin_config_t pins = {};
    pins.mck_io_num = I2S_PIN_NO_CHANGE;
    pins.bck_io_num = PIN_I2S_BCLK;
    pins.ws_io_num = PIN_I2S_LRC;
    pins.data_out_num = PIN_I2S_DOUT;
    pins.data_in_num = I2S_PIN_NO_CHANGE;
    if (i2s_driver_install(PORT, &c, 0, nullptr) != ESP_OK || i2s_set_pin(PORT, &pins) != ESP_OK) {
        Serial.println(F("Sound: I2S setup failed"));
        return;
    }
    if (xTaskCreate(soundTask, "sound", 4096, nullptr, 3, &task) != pdPASS) {
        task = nullptr;
        Serial.println(F("Sound: no memory for the player task"));
    }
}

void soundPlay(uint8_t id, bool ring) {
    if (id >= SND_COUNT) return;
    Serial.printf("Sound: %s%s, volume %u\n", TUNES[id].name, ring ? " (ringing)" : "", cfg.volume);
    request({{&TUNES[id]}, 1, ring});
}

void soundCue(uint8_t style, SwCue cue) {
    if (style == SWS_OFF || style >= SWS_COUNT || ringing) return;
    request({{&CUES[style - 1][cue]}, 1, false});
}

void soundDemoCues(uint8_t style) {
    if (style == SWS_OFF || style >= SWS_COUNT) return;
    Serial.printf("Sound: stopwatch style %s\n", swSoundName(style));
    const Tune* c = CUES[style - 1];
    request({{&c[CUE_START], &c[CUE_PAUSE], &c[CUE_RESET]}, 3, false});
}

void soundStop() {
    request({{nullptr}, 0, false});
}

bool soundPlaying() {
    return playing;
}
