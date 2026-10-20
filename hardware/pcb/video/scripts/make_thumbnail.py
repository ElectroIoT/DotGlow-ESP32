"""PCB video thumbnails -> docs/pcb/thumb-pcb-short.jpg (1080x1920) and docs/pcb/thumb-pcb-wide.jpg (1280x720).

    python hardware/pcb/video/scripts/make_thumbnail.py
"""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
IMG = os.path.join(ROOT, "hardware", "pcb", "video", "assets", "img")
OUT = os.path.join(ROOT, "docs", "pcb")
F = r"C:\Windows\Fonts"


def font(n, s):
    return ImageFont.truetype(os.path.join(F, n), s)


def base(w, h):
    im = Image.new("RGB", (w, h), (7, 8, 12))
    d = ImageDraw.Draw(im)
    for y in range(18, h, 34):
        for x in range(18, w, 34):
            d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(52, 14, 16))
    return im


def glow(im, box, a=110):
    g = Image.new("RGB", im.size, (0, 0, 0))
    ImageDraw.Draw(g).ellipse(box, fill=(255, 59, 59))
    g = g.filter(ImageFilter.GaussianBlur(110))
    return Image.composite(Image.blend(im, g, 0.6), im, Image.new("L", im.size, a))


def board(path, width, angle=0):
    b = Image.open(os.path.join(IMG, path)).convert("RGBA")
    b = b.resize((width, int(b.height * width / b.width)), Image.LANCZOS)
    m = Image.new("L", b.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, b.width - 1, b.height - 1), 14, fill=255)
    b.putalpha(m)
    return b.rotate(angle, expand=True, resample=Image.BICUBIC) if angle else b


def shadow_paste(im, b, pos, off=(24, 34)):
    s = b.getchannel("A").filter(ImageFilter.GaussianBlur(26)).point(lambda v: int(v * 0.85))
    im.paste((0, 0, 0), (pos[0] + off[0], pos[1] + off[1]), s)
    im.paste(b, pos, b)


def centered(d, text, y, f, fill, w):
    tw = d.textlength(text, font=f)
    d.text(((w - tw) / 2, y), text, font=f, fill=fill)


# ---- vertical 1080 x 1920 (Shorts)
W, H = 1080, 1920
im = glow(base(W, H), (-100, 380, 1180, 1500))
b = board("top-blue.jpg", 1240, 90)          # tall board, antenna end at the bottom
shadow_paste(im, b, ((W - b.width) // 2, 490))
d = ImageDraw.Draw(im)
d.rounded_rectangle((60, 96, 520, 168), 36, fill=(255, 59, 59))
d.text((92, 108), "OPEN HARDWARE", font=font("segoeuib.ttf", 42), fill=(255, 255, 255))
d.text((60, 196), "I MADE MY OWN", font=font("segoeuib.ttf", 112), fill=(255, 255, 255))
d.text((60, 312), "PCB!", font=font("segoeuib.ttf", 150), fill=(255, 59, 59))
d.text((60, 1830), "ElectroIoT.in", font=font("segoeuib.ttf", 40), fill=(255, 255, 255))
d.text((60, 1760), "ESP32-S3 + USB-C + speaker  |  DotGlow V1", font=font("segoeuib.ttf", 40), fill=(255, 224, 138))
im.convert("RGB").save(os.path.join(OUT, "thumb-pcb-short.jpg"), quality=92)

# ---- wide 1280 x 720 (YouTube / link previews)
W, H = 1280, 720
im = glow(base(W, H), (200, 220, 1380, 760))
b = board("top-blue.jpg", 1000, -4)
shadow_paste(im, b, (270, 330))
d = ImageDraw.Draw(im)
d.text((50, 30), "I MADE MY OWN", font=font("segoeuib.ttf", 92), fill=(255, 255, 255))
d.text((50, 130), "PCB!", font=font("segoeuib.ttf", 130), fill=(255, 59, 59))
d.text((470, 160), "Schematic to 3D", font=font("segoeuib.ttf", 58), fill=(255, 224, 138))
d.text((470, 235), "ESP32-S3 + USB-C + speaker", font=font("segoeui.ttf", 40), fill=(205, 210, 220))
d.text((W - 270, H - 56), "ElectroIoT.in", font=font("segoeuib.ttf", 34), fill=(255, 255, 255))
im.convert("RGB").save(os.path.join(OUT, "thumb-pcb-wide.jpg"), quality=92)
print("thumbnails done")
