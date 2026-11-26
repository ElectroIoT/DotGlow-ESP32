// Speaker: a MAX98357A I2S amplifier. Every sound is synthesised on the chip (no audio files)
// by a small task of its own, so nothing here blocks the main loop. With no amplifier wired
// the pins just toggle and nothing else changes.
#pragma once

#include <Arduino.h>

// Alarm and countdown sounds. Stored in flash (settings): only ever append.
enum SoundId : uint8_t {
    SND_BEEP, SND_DIGITAL, SND_CHIME, SND_BELL, SND_RISE,
    SND_MARIMBA, SND_BIRDS, SND_ARCADE, SND_SIREN, SND_PULSE, SND_COUNT
};

// Stopwatch sound styles. Stored in flash: only ever append.
enum SwSound : uint8_t { SWS_OFF, SWS_BEEP, SWS_CLICK, SWS_ARCADE, SWS_WHISTLE, SWS_COUNT };
enum SwCue : uint8_t { CUE_START, CUE_PAUSE, CUE_RESET };

static const uint8_t MAX_VOLUME = 10;

void        soundBegin();                          // I2S + amplifier; until called, nothing plays
void        soundPlay(uint8_t id, bool ring);      // ring: repeat until soundStop(), getting louder
void        soundCue(uint8_t style, SwCue cue);    // stopwatch cue; ignored while something rings
void        soundDemoCues(uint8_t style);          // preview: start, pause and reset one after another
void        soundStop();
bool        soundPlaying();
const char* soundName(uint8_t id);
const char* swSoundName(uint8_t style);
