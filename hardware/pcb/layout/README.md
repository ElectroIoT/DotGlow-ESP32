# DotGlow V1 layout only (no routing)

For building your own board in EasyEDA with your own parts. No copper tracks, just the outline and part positions.

| File | Use |
|---|---|
| `dotglow-v1-layout.png` / `.pdf` | picture of the outline, holes, keep-out and part positions |
| `dotglow-v1-outline-holes.dxf` | **start here**: board outline 128 x 33, four 3.2 mm mounting holes, antenna keep-out, display header pins, USB-C (separate layers, mm, origin bottom-left, Y up) |
| `dotglow-v1-full-layout.dxf` | everything in one file: outline, part courtyards, silkscreen, drawings (mm, origin bottom-left) |
| `dotglow-v1-placement.csv` | every part: ref, value, footprint, part, **X / Y in mm from the top-left corner (X right, Y down)**, rotation |
| `kicad/` | the same placement as a KiCad project (placed, not routed) |

## Board

- 128 x 33 mm, two layers, origin at the top-left corner.
- **ESP32 antenna keep-out: X < 6.9 mm, full height.** No copper, no parts, no pour there. The ESP32-S3-WROOM-1 (25.5 x 18 mm) sits at the left edge, antenna end to the left.
- Mounting holes `H1..H4` (3.2 mm for M3) are **placeholders**: (23.5, 3), (21, 30), (125, 3), (125, 30). Move them to match your matrix module.
- `J2` (5-pin DISPLAY IN header, VCC GND DIN CS CLK) is at (125.5, 11.42), vertical (pin 1 at the top, 2.54 mm pitch). Move it to match your matrix module.
- USB-C `J1` (108, 29) sits on the bottom edge. The speaker JST `J5` and the solder pads `TP1` / `TP2` are next to the buttons.

## EasyEDA import

- File > Import > DXF, pick `dotglow-v1-outline-holes.dxf` (units: mm).
- Or File > Import > KiCad, `kicad/dotglow-v1.kicad_pcb`, and swap the footprints for your own parts. Keep the positions from the CSV.
- Net names and pin assignments are in `../README.md` (GPIO table) and `kicad/dotglow-v1.kicad_sch`.
