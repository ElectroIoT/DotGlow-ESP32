"""Silkscreen-ready logos (transparent PNG, black art) -> docs/pcb/logos/

    python hardware/pcb/video/scripts/make_logos.py

PCBWay logo comes from docs/pcb/pcbway-logo-silk.png (already black on white). In EasyEDA: Place > Image, choose the PNG,
set the layer to Top Silkscreen, size the width to about 20 mm (min line width of the art stays above 0.15 mm).
"""
import os

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
OUT = os.path.join(ROOT, "docs", "pcb", "logos")
os.makedirs(OUT, exist_ok=True)
FONT = r"C:\Windows\Fonts\segoeuib.ttf"


def to_alpha(img_l, color):
    """black art on white (mode L) -> RGBA of `color` with alpha = darkness."""
    a = img_l.point(lambda v: 255 - v)
    out = Image.new("RGBA", img_l.size, color + (0,))
    out.putalpha(a)
    return out


def trim(img):
    bb = img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    return img.crop(bb)


def save(name, art_l):
    for tag, color in (("black", (0, 0, 0)), ("white", (255, 255, 255))):
        im = trim(to_alpha(art_l, color))
        pad = Image.new("RGBA", (im.width + 40, im.height + 40), (0, 0, 0, 0))
        pad.paste(im, (20, 20))
        pad.save(os.path.join(OUT, f"{name}-{tag}.png"))
        print(name, tag, pad.size)


# ---- PCBWay (from the supplied logo)
src = Image.open(os.path.join(ROOT, "docs", "pcb", "pcbway-logo-silk.png")).convert("L")
save("pcbway", src)

# ---- ElectroIoT.in: 5x7 dot-matrix "E" + wordmark
S = 4  # supersample
H = 540 * S
f = ImageFont.truetype(FONT, 250 * S)
text = "ElectroIoT"
tw = int(f.getlength(text))
dot_w = 5 * 70 * S
W = dot_w + 60 * S + tw + int(f.getlength(".in") * 0.62) + 40 * S
art = Image.new("L", (W, H), 255)
d = ImageDraw.Draw(art)
E = ["11111", "10000", "10000", "11110", "10000", "10000", "11111"]
step = 70 * S
r = 26 * S
y0 = (H - 7 * step) // 2 + step // 2
for j, row in enumerate(E):
    for i, c in enumerate(row):
        if c == "1":
            cx, cy = step // 2 + i * step, y0 + j * step
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0)
x = dot_w + 60 * S
d.text((x, H // 2), text, font=f, fill=0, anchor="lm")
fs = ImageFont.truetype(FONT, int(250 * S * 0.62))
d.text((x + tw + 6 * S, H // 2 + 28 * S), ".in", font=fs, fill=0, anchor="lm")
art = art.resize((W // S, H // S), Image.LANCZOS)
art = art.point(lambda v: 0 if v < 140 else 255)
save("electroiot-in", art)

# icon only (square), good for a small corner mark
ic = Image.new("L", (5 * 70 * S, 7 * 70 * S), 255)
di = ImageDraw.Draw(ic)
for j, row in enumerate(E):
    for i, c in enumerate(row):
        if c == "1":
            cx, cy = step // 2 + i * step, step // 2 + j * step
            di.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0)
ic = ic.resize((ic.width // S, ic.height // S), Image.LANCZOS).point(lambda v: 0 if v < 140 else 255)
save("electroiot-dot-e", ic)
