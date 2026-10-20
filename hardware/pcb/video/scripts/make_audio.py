"""Original music + sound effects for the PCB short (numpy only, nothing copyrighted by anyone else).

    python scripts/make_audio.py   ->  assets/audio/music.wav (34 s), whoosh.wav, tick.wav, ding.wav
"""
import os
import wave

import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "audio")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(11)


def save(name, x, peak=0.9):
    x = np.asarray(x, np.float64)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    m = np.abs(x).max()
    if m > 0:
        x = x / m * peak
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(os.path.join(OUT, name), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def tt(d):
    return np.arange(int(d * SR)) / SR


def env(n, a=0.005, r=0.2):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] = np.linspace(1, 0, nr)
    return e


def note(f, d, kind="saw"):
    t = tt(d)
    if kind == "saw":
        x = sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 6))
    else:
        x = np.sin(2 * np.pi * f * t)
    return x * env(len(t), 0.01, min(0.25, d * 0.6))


DUR = 34.0
BPM = 112
beat = 60 / BPM
mix = np.zeros(int(DUR * SR))
# chord progression Am - F - C - G (bass + pad + arp)
chords = [(220.0, [220.0, 261.6, 329.6]), (174.6, [174.6, 220.0, 261.6]),
          (261.6, [261.6, 329.6, 392.0]), (196.0, [196.0, 246.9, 293.7])]
bar = beat * 4
nbars = int(DUR / bar) + 1
for b in range(nbars):
    root, tri = chords[b % 4]
    t0 = b * bar
    # pad
    for f in tri:
        s = note(f, bar, "sin") * 0.10
        i = int(t0 * SR)
        mix[i:i + len(s)] += s[:len(mix) - i]
    # bass on beats 1 and 3
    for k in (0, 2):
        s = note(root / 2, beat * 1.6, "sin") * 0.34
        i = int((t0 + k * beat) * SR)
        mix[i:i + len(s)] += s[:max(0, len(mix) - i)]
    # arpeggio, 8th notes
    for k in range(8):
        f = tri[k % 3] * (2 if k % 2 else 1)
        s = note(f * 2, beat / 2 * 0.9, "saw") * 0.07
        i = int((t0 + k * beat / 2) * SR)
        mix[i:i + len(s)] += s[:max(0, len(mix) - i)]
    # soft kick on every beat after bar 3, hat on offbeats
    if b >= 3:
        for k in range(4):
            t = tt(0.22)
            kk = np.sin(2 * np.pi * (110 * np.exp(-t * 18) + 40) * t) * np.exp(-t * 14) * 0.5
            i = int((t0 + k * beat) * SR)
            mix[i:i + len(kk)] += kk[:max(0, len(mix) - i)]
            h = np.diff(rng.standard_normal(int(0.05 * SR) + 1)) * np.exp(-tt(0.05) * 70) * 0.10
            i = int((t0 + k * beat + beat / 2) * SR)
            mix[i:i + len(h)] += h[:max(0, len(mix) - i)]
mix *= np.minimum(1.0, np.linspace(0, 1, len(mix)) * DUR / 2.0)          # fade in 2 s
mix *= np.minimum(1.0, (DUR - np.arange(len(mix)) / SR) / 2.5)             # fade out 2.5 s
save("music.wav", mix, 0.8)

# whoosh: filtered noise sweep
t = tt(0.7)
n = rng.standard_normal(len(t))
k = np.exp(-((t - 0.35) / 0.18) ** 2)
sw = np.convolve(n, np.ones(40) / 40, mode="same") * k
save("whoosh.wav", sw * env(len(t), 0.02, 0.3), 0.8)

# tick: short click
t = tt(0.06)
save("tick.wav", np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 90), 0.8)

# ding: two bell partials
t = tt(0.9)
save("ding.wav", (np.sin(2 * np.pi * 1318 * t) + 0.5 * np.sin(2 * np.pi * 1975 * t)) * np.exp(-t * 5), 0.8)
print("audio done")
