"""
Layout-only files for EasyEDA: placement CSV, outline+holes DXF, and a cropped PNG of the layout PDF.
Run after generate_kicad.py has written hardware/pcb/layout/kicad (see rebuild.ps1).

    python hardware/pcb/make_layout_files.py
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LAYOUT = os.path.join(HERE, "layout")
os.environ["DG_OUT"] = os.path.join(LAYOUT, "kicad")
sys.path.insert(0, HERE)
import generate_kicad as g  # noqa: E402

# ---- placement CSV (X right, Y down, mm from the top-left corner)
with open(os.path.join(LAYOUT, "dotglow-v1-placement.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Ref", "Value", "Footprint", "Part / MPN", "X_mm", "Y_mm", "Rot_deg", "Note"])
    w.writerow(["#", "board outline", "", "", 0, 0, 0, f"{g.BOARD_W:g} x {g.BOARD_H:g} mm, origin = top-left corner, X right, Y down"])
    w.writerow(["#", "antenna keep-out", "", "", 0, 0, 0, f"no copper / parts for X < {g.ANT_KEEPOUT_X:g} mm (full height)"])
    for p in g.parts:
        x, y, rot = p["pcb"]
        w.writerow([p["ref"], p["value"], p["fp"].split(":")[1], p["mpn"], round(x, 2), round(y, 2), rot, p["note"]])

# ---- DXF: outline, holes, keep-out, display header, USB-C (mm, origin bottom-left, Y up)
import ezdxf  # noqa: E402

d = ezdxf.new("R2010", setup=True)
d.units = ezdxf.units.MM
for name, col in (("BOARD_OUTLINE", 7), ("MOUNT_HOLES_3.2mm", 1), ("ANTENNA_KEEPOUT", 6), ("DISPLAY_HEADER", 3), ("USB_C", 4)):
    d.layers.add(name, color=col)
m = d.modelspace()
W, H = g.BOARD_W, g.BOARD_H
fy = lambda y: round(H - y, 3)  # noqa: E731
m.add_lwpolyline([(0, 0), (W, 0), (W, H), (0, H)], close=True, dxfattribs={"layer": "BOARD_OUTLINE"})
pl = {p["ref"]: p["pcb"] for p in g.parts}
for ref, (x, y, _) in pl.items():
    if ref.startswith("H"):
        m.add_circle((x, fy(y)), 1.6, dxfattribs={"layer": "MOUNT_HOLES_3.2mm"})
k = g.ANT_KEEPOUT_X
m.add_lwpolyline([(0, 0), (k, 0), (k, H), (0, H)], close=True, dxfattribs={"layer": "ANTENNA_KEEPOUT"})
x, y, _ = pl["J2"]  # 1x05 header, pin 1 at (x, y), pitch 2.54 going down
for i in range(5):
    m.add_circle((x, fy(y + i * 2.54)), 0.5, dxfattribs={"layer": "DISPLAY_HEADER"})
x, y, _ = pl["J1"]
m.add_lwpolyline([(x - 4.5, 0), (x + 4.5, 0), (x + 4.5, fy(y)), (x - 4.5, fy(y))], close=True, dxfattribs={"layer": "USB_C"})
d.saveas(os.path.join(LAYOUT, "dotglow-v1-outline-holes.dxf"))

# ---- PNG from the PDF (cropped to the drawing)
import pymupdf  # noqa: E402
from PIL import Image, ImageChops  # noqa: E402

pdf = pymupdf.open(os.path.join(LAYOUT, "dotglow-v1-layout.pdf"))
png = os.path.join(LAYOUT, "dotglow-v1-layout.png")
pdf[0].get_pixmap(dpi=300).save(png)
im = Image.open(png).convert("RGB")
bb = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox()
im.crop((bb[0] - 30, bb[1] - 30, bb[2] + 30, bb[3] + 30)).save(png)
print("layout files written")
