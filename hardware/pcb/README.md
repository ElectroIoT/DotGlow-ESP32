# DotGlow V1 board (ESP32-S3 + USB-C + speaker), 128 x 33 mm

A two-layer carrier that stacks on the back of a common **MAX7219 4-in-1 (FC-16, 8 x 32) LED matrix module**
(128 x 33 x 15 mm, M3 holes, handsontec datasheet DSP-1172). It replaces the dev board and the jumper wires.

> **Status: V1 draft, never built or tested.** It is meant to be reviewed and then redrawn or adjusted by hand in
> EasyEDA (or KiCad). Read "Check before you order" first.

KiCad 10 project: [`kicad/dotglow-v1.kicad_pro`](kicad/dotglow-v1.kicad_pro) ·
Top: [`renders/pcb_top.png`](renders/pcb_top.png) · Bottom: [`renders/pcb_bottom.png`](renders/pcb_bottom.png) ·
Schematic: [`renders/schematic.pdf`](renders/schematic.pdf) · BOM: [`fab/dotglow-v1-bom.csv`](fab/dotglow-v1-bom.csv) ·
Gerbers: `fab/dotglow-v1-gerbers-jlcpcb.zip`

EasyEDA: File > Import > KiCad (the `.kicad_pcb` and `.kicad_sch`), or use the pin table below and draw it yourself.

## What is on it

| Block | Parts |
|---|---|
| MCU | ESP32-S3-WROOM-1-N16R8 (LCSC C2913202, 25.5 x 18 mm), antenna end at the left board edge, copper keep-out. Full pinout: [ESP32-S3-WROOM-1-PINOUT.md](ESP32-S3-WROOM-1-PINOUT.md) |
| Power | USB-C (5 V only, CC 5.1k), AP2112K-3.3 regulator (600 mA), 22 uF bulk, power LED |
| USB data | D+/D- to the ESP32-S3 native USB (flash and serial log), USBLC6-2SC6 ESD protection |
| Display | 74AHCT125 shifts the 3.3 V SPI signals to 5 V for the MAX7219, 5-pin header VCC GND DIN CS CLK |
| Audio | MAX98357A (LCSC C910544) I2S amplifier, JST PH 2-pin + two solder pads for the 8 ohm 2 W 2030 speaker |
| Buttons | RESET (EN), BOOT (GPIO0), STOPWATCH (GPIO4) |
| Sensors | NTC 10k temperature (GPIO2), LDR header (GPIO1), DHT22 header (GPIO13), I2C header (GPIO8/9) for an RTC in V2 |

No RTC chip in V1: the time comes from NTP over WiFi and from the phone over Bluetooth. The I2C header is there for V2.

## GPIO map (matches `src/config.h`, so the existing firmware works unchanged)

| GPIO | Net | Use |
|---|---|---|
| 0 | BOOT | `PIN_BUTTON`, boot-mode strap |
| 1 | LDR_ADC | `PIN_LDR` (optional LDR) |
| 2 | NTC_ADC | NTC thermistor divider (new, needs firmware) |
| 4 | STOPWATCH | `PIN_STOPWATCH` |
| 5 / 6 / 7 | I2S_BCLK / I2S_LRC / I2S_DIN | MAX98357A (new, needs firmware) |
| 8 / 9 | I2C_SDA / I2C_SCL | header for RTC / sensors |
| 10 / 11 / 12 | CS / MOSI(DIN) / CLK | `PIN_CS` and the S3 default SPI pins, through the 74AHCT125 |
| 13 | DHT_DATA | optional DHT22 |
| 15 | AMP_SD | amplifier mute / shutdown |
| 19 / 20 | USB D- / D+ | native USB (module pins 13 / 14) |

Strapping pins 3, 45, 46 are left unused.

## Circuit notes

- 5 V comes only from the USB-C connector and feeds the matrix module directly (full brightness can draw about 1 A,
  use a 5 V / 1 A or better charger and a good cable).
- The MAX7219 needs a logic high of at least 3.5 V at 5 V supply. The 74AHCT125 makes that certain; the 4th gate is parked.
- MAX98357A: GAIN_SLOT floating = 9 dB; SD_MODE has a 100k pull-up to 3V3 (on, left+right mix) and GPIO15 can pull it low.
  Speaker output is bridge-tied: neither speaker wire is ground.
- GPIO0 BOOT and EN RESET give the standard USB flashing sequence (hold BOOT, tap RESET).

## Check before you order

| Item | What to verify |
|---|---|
| **Matrix module** | The M3 hole positions and the 5-pin IN header position are **placeholders**. Measure YOUR module and move `H1..H4` and `J2` in `generate_kicad.py` (PLACE table), or in EasyEDA. Check the header order (VCC GND DIN CS CLK) on your module |
| Back of the module | Height of the MAX7219 chips and header pins under the new board (stack with 8-10 mm standoffs, or add cutouts) |
| Antenna | The left 6.9 mm of the board is a copper keep-out. Keep the speaker magnet and metal case away from it |
| ESP32 footprint | KiCad `RF_Module:ESP32-S3-WROOM-1` (same module). Compare with the Espressif datasheet. N16R8 has octal PSRAM, so IO35-37 are not usable |
| Speaker | 2030 cavity speaker: confirm size, thickness and lead/connector type, then set the JST or use the solder pads |
| Parts | Pick LCSC parts that match the footprints (0805 passives, B3S-style 6x6 tact switches, GCT USB4105 or an equal USB-C) |
| DRC | The generated board is auto-routed with a small built-in router: review the routing before ordering |

## Rebuild

```text
set TG_NO_ZONES=1
"%LOCALAPPDATA%\Programs\KiCad\10.0\bin\python.exe" hardware\pcb\generate_kicad.py
"%LOCALAPPDATA%\Programs\KiCad\10.0\bin\python.exe" hardware\pcb\route_pcb.py
python hardware\pcb\export_fab.py
```

Edit the netlist and floor plan in `generate_kicad.py` (single source of truth), not the generated files.
