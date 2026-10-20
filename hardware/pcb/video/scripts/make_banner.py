"""README banner for the DotGlow V1 board -> docs/pcb/banner-pcb-v1.png (1600 x 560).

    python hardware/pcb/video/scripts/make_banner.py
"""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
IMG = os.path.join(ROOT, "hardware", "pcb", "video", "assets", "img")
OUT = os.path.join(ROOT, "docs", "pcb", "banner-pcb-v1.png")
W, H = 1600, 560
FONTS = r"C:\Windows\Fonts"


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


bg = Image.new("RGB", (W, H), (7, 8, 12))
px = ImageDraw.Draw(bg)
# red LED-dot grid, fading to the right
for y in range(16, H, 28):
    for x in range(16, W, 28):
        a = max(0.0, 1.0 - x / W * 0.9)
        c = (int(255 * 0.30 * a + 14), int(59 * 0.30 * a + 8), int(59 * 0.30 * a + 10))
        px.ellipse((x - 2, y - 2, x + 2, y + 2), fill=c)

# glow behind the board
glow = Image.new("RGB", (W, H), (0, 0, 0))
gd = ImageDraw.Draw(glow)
gd.ellipse((640, 120, 1600, 520), fill=(255, 59, 59))
glow = glow.filter(ImageFilter.GaussianBlur(120))
bg = Image.blend(bg, Image.eval(glow, lambda v: v), 0.0)
bg = Image.composite(Image.blend(bg, glow, 0.5), bg, Image.new("L", (W, H), 90))

# the real 3D render of the board (blue), slightly rotated
board = Image.open(os.path.join(IMG, "top-blue.jpg")).convert("RGBA")
bw = 880
board = board.resize((bw, int(board.height * bw / board.width)), Image.LANCZOS)
mask = Image.new("L", board.size, 0)
ImageDraw.Draw(mask).rounded_rectangle((0, 0, board.width - 1, board.height - 1), 10, fill=255)
board.putalpha(mask)
board = board.rotate(-6, expand=True, resample=Image.BICUBIC)
shadow = Image.new("RGBA", board.size, (0, 0, 0, 0))
shadow.putalpha(board.getchannel("A").filter(ImageFilter.GaussianBlur(24)).point(lambda v: int(v * 0.8)))
bx, by = 690, 190
bg.paste((0, 0, 0), (bx + 20, by + 40), shadow.getchannel("A"))
bg.paste(board, (bx, by), board)

d = ImageDraw.Draw(bg)
d.text((64, 70), "ELECTROIOT  /  OPEN HARDWARE", font=font("segoeuib.ttf", 26), fill=(255, 120, 110))
d.text((60, 110), "DotGlow", font=font("segoeuib.ttf", 118), fill=(255, 255, 255))
d.text((62, 238), "V1 Board", font=font("segoeuib.ttf", 74), fill=(255, 59, 59))
d.text((64, 340), "ESP32-S3 + USB-C + I2S speaker amplifier\nfor the MAX7219 4-in-1 LED matrix clock",
       font=font("segoeui.ttf", 30), fill=(205, 210, 220), spacing=8)

x = 64
for t in ("128 x 31.1 mm", "2 layers", "KiCad + EasyEDA + Gerber"):
    f = font("segoeuib.ttf", 24)
    w = d.textlength(t, font=f) + 36
    d.rounded_rectangle((x, 460, x + w, 506), 23, fill=(255, 59, 59) if x == 64 else (30, 34, 44), outline=(255, 59, 59), width=2)
    d.text((x + 18, 468), t, font=f, fill=(255, 255, 255))
    x += w + 14

d.text((W - 250, 60), "ElectroIoT.in", font=font("segoeuib.ttf", 30), fill=(255, 255, 255))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bg.save(OUT)
print(OUT, bg.size)
