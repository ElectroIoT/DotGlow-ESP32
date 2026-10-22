# Hardware

Everything physical for DotGlow lives here.

| Folder | What is in it |
|---|---|
| [`pcb/`](pcb/README.md) | **DotGlow V1 board**: a custom ESP32-S3 + USB-C + speaker PCB that stacks behind the 4-in-1 MAX7219 module |
| [`pcb/bom/`](pcb/bom/README.md) | bill of materials (xlsx, csv, readable table) |
| [`pcb/easyeda/`](pcb/easyeda) | the final EasyEDA design exports: schematic PDF, PCB PDF, BOM, Gerber zip |
| [`enclosure/`](enclosure) | 3D-printable cases (OpenSCAD + ready STL files) for ESP32 / ESP8266 dev boards |

Just want to build a clock? You do not need the PCB: wire any ESP32 / ESP32-S3 dev board to the display as shown in the
[main README](../README.md#wiring), then print a case from `enclosure/`.
