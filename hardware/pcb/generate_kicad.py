"""
Generate the DotGlow V1 board KiCad project (schematic + placed PCB) from ONE netlist.

Run with KiCad's bundled Python (it provides the `pcbnew` module):
    "%LOCALAPPDATA%/Programs/KiCad/10.0/bin/python.exe" hardware/pcb/generate_kicad.py

Outputs into hardware/kicad/:
    dotglow-v1.kicad_pro / .kicad_sch / .kicad_pcb

The schematic connects every pin with a short wire + net label (no long wires), so the
netlist below is the single source of truth. The PCB is PLACED but NOT ROUTED.
"""
import copy
import json
import math
import os
import re
import uuid

KICAD = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs/KiCad/10.0/share/kicad").replace("\\", "/")
if not os.path.isdir(KICAD):
    KICAD = "C:/Program Files/KiCad/10.0/share/kicad"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("DG_OUT") or os.path.join(HERE, "kicad")
NAME = "dotglow-v1"
PROJECT_UUID_NS = uuid.UUID("3d9a41b2-52c7-4f43-8b1e-7a0c9e5d2f11")



def uid(*parts):
    """Deterministic UUIDs so regenerating keeps KiCad links stable."""
    return str(uuid.uuid5(PROJECT_UUID_NS, "/".join(str(p) for p in parts)))


# ============================================================================
# S-expression helpers
# ============================================================================
class Q(str):
    """A quoted string atom."""


def parse(text):
    tokens = re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()"]+', text)
    stack = [[]]
    for t in tokens:
        if t == "(":
            stack.append([])
        elif t == ")":
            node = stack.pop()
            stack[-1].append(node)
        elif t.startswith('"'):
            stack[-1].append(Q(t[1:-1].replace('\\"', '"').replace("\\\\", "\\")))
        else:
            stack[-1].append(t)
    return stack[0][0]


def dump(node, indent=0):
    if isinstance(node, list):
        if not any(isinstance(c, list) for c in node):
            return "(" + " ".join(dump(c) for c in node) + ")"
        pad = "\t" * (indent + 1)
        inner = []
        for c in node:
            inner.append(dump(c, indent + 1) if isinstance(c, list) else dump(c))
        head = []
        rest = []
        for c, s in zip(node, inner):
            (rest if (isinstance(c, list) or rest) else head).append(s)
        return "(" + " ".join(head) + "".join("\n" + pad + s for s in rest) + "\n" + "\t" * indent + ")"
    if isinstance(node, Q):
        return '"' + node.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(node, float):
        s = f"{node:.4f}".rstrip("0").rstrip(".")
        return s if s not in ("-0", "") else "0"
    return str(node)


def find(node, head):
    return [c for c in node if isinstance(c, list) and c and c[0] == head]


def first(node, head):
    r = find(node, head)
    return r[0] if r else None


# ============================================================================
# Symbol library access (with `extends` flattening)
# ============================================================================
_lib_cache = {}


def lib_symbols(lib):
    if lib not in _lib_cache:
        path = os.path.join(KICAD, "symbols", lib + ".kicad_sym")
        _lib_cache[lib] = {s[1]: s for s in find(parse(open(path, encoding="utf-8").read()), "symbol")}
    return _lib_cache[lib]



CUSTOM_SYMBOLS_TEXT = r"""
(kicad_symbol_lib (version 20241209) (generator "tg_gen"))
"""
_lib_cache["ct6"] = {}

def flat_symbol(lib, name):
    syms = lib_symbols(lib)
    sym = copy.deepcopy(syms[name])
    ext = first(sym, "extends")
    if ext:
        base = flat_symbol(lib, ext[1])
        base_name = ext[1]
        # override properties from derived symbol
        props = {p[1]: p for p in find(sym, "property")}
        out = [c for c in base if not (isinstance(c, list) and c and c[0] == "property" and c[1] in props)]
        # insert derived properties after head items
        idx = next(i for i, c in enumerate(out) if isinstance(c, list) and c[0] == "property") if any(
            isinstance(c, list) and c and c[0] == "property" for c in out) else 2
        out[idx:idx] = list(props.values())
        for c in out:
            if isinstance(c, list) and c and c[0] == "symbol" and c[1].startswith(base_name + "_"):
                c[1] = Q(name + c[1][len(base_name):])
        out[1] = Q(name)
        sym = out
    return sym


def embedded_symbol(lib_id):
    lib, name = lib_id.split(":")
    sym = flat_symbol(lib, name)
    sym[1] = Q(lib_id)
    return sym


def symbol_pins(lib_id):
    """-> {unit: [(number, x, y, angle, type)]} ; unit 0 = common to all units."""
    lib, name = lib_id.split(":")
    sym = flat_symbol(lib, name)
    units = {}
    for sub in find(sym, "symbol"):
        m = re.match(r".*_(\d+)_(\d+)$", sub[1])
        u, style = int(m.group(1)), int(m.group(2))
        if style > 1:
            continue
        for p in find(sub, "pin"):
            at = first(p, "at")
            num = first(p, "number")[1]
            units.setdefault(u, []).append((str(num), float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0, p[1]))
    return units



# ============================================================================
# The netlist  (single source of truth for schematic AND pcb)
# ============================================================================
FP_R = "Resistor_SMD:R_0805_2012Metric"
FP_R06 = "Resistor_SMD:R_0603_1608Metric"
FP_C = "Capacitor_SMD:C_0805_2012Metric"
FP_C_BIG = "Capacitor_SMD:C_1206_3216Metric"

parts = []


def part(ref, lib_id, value, fp, pins, sch, pcb=None, rot=0, mpn="", note=""):
    parts.append(dict(ref=ref, lib_id=lib_id, value=value, fp=fp, pins=pins, sch=sch,
                      pcb=pcb, rot=rot, mpn=mpn, note=note))


def symbol_pin_names(lib_id):
    lib, name = lib_id.split(":")
    sym = flat_symbol(lib, name)
    out = {}

    def walk(n):
        for c in n:
            if isinstance(c, list) and c and c[0] == "pin":
                out[str(first(c, "number")[1])] = str(first(c, "name")[1])
            elif isinstance(c, list):
                walk(c)
    walk(sym)
    return out


# ---- ESP32-S3-WROOM-1-N16R8 (LCSC C2913202). Pins are assigned BY NAME, every GND pad goes to GND.
# N16R8 has octal PSRAM: IO35, IO36, IO37 are used inside the module and must stay unconnected.
# GPIOs 0/4/10/11/12/1 are the pins the DotGlow firmware already uses on the ESP32-S3 (src/config.h).
ESP_NETS = {
    "3V3": "+3V3", "EN": "EN",
    "IO0": "BOOT",            # PIN_BUTTON (hold 5 s = WiFi setup, hold 10 s = pairing PIN reset) + boot-mode strap
    "IO4": "STOPWATCH",       # PIN_STOPWATCH
    "IO1": "LDR_ADC",         # PIN_LDR (optional LDR from 3V3, 10k to GND on the board)
    "IO2": "NTC_ADC",         # 10k NTC thermistor divider (temperature), new
    "IO10": "MAX_CS_3V",      # PIN_CS  (SPI CS  -> 74AHCT125 -> display CS)
    "IO11": "MAX_DIN_3V",     # SPI MOSI -> 74AHCT125 -> display DIN
    "IO12": "MAX_CLK_3V",     # SPI CLK  -> 74AHCT125 -> display CLK
    "IO5": "I2S_BCLK", "IO6": "I2S_LRC", "IO7": "I2S_DIN",   # MAX98357A amplifier (new)
    "IO15": "AMP_SD",         # amplifier shutdown / mute (new)
    "IO8": "I2C_SDA", "IO9": "I2C_SCL",   # header for an RTC (V2) or other I2C module
    "IO13": "DHT_DATA",       # optional DHT22 header
    "USB_D-": "USB_DN", "USB_D+": "USB_DP",
}
_names = symbol_pin_names("RF_Module:ESP32-S3-WROOM-1")
ESP_PINS = {}
for _num, _nm in _names.items():
    if _nm == "GND":
        ESP_PINS[_num] = "GND"
    elif _nm in ESP_NETS:
        ESP_PINS[_num] = ESP_NETS[_nm]
part("U1", "RF_Module:ESP32-S3-WROOM-1", "ESP32-S3-WROOM-1-N16R8", "RF_Module:ESP32-S3-WROOM-1", ESP_PINS, (70, 130),
     mpn="ESP32-S3-WROOM-1-N16R8 (LCSC C2913202)",
     note="25.5 x 18 mm, PCB antenna at the left end: keep copper and parts out of the antenna zone; IO35-37 not usable (octal PSRAM)")

# ---- USB-C power + native USB (flashing, serial log)
part("J1", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C 5V", "Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal",
     {"A1": "GND", "B1": "GND", "A12": "GND", "B12": "GND", "A4": "+5V", "B4": "+5V", "A9": "+5V", "B9": "+5V",
      "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN", "A8": None, "B8": None,
      "SH": "GND"}, (190, 40), mpn="GCT USB4105-GF-A")
part("R9", "Device:R", "5.1k", FP_R, {"1": "CC1", "2": "GND"}, (225, 30), note="CC pull-down: asks a USB charger for 5 V")
part("R10", "Device:R", "5.1k", FP_R, {"1": "CC2", "2": "GND"}, (240, 30))
part("U5", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
     {"1": "USB_DP", "6": "USB_DP", "3": "USB_DN", "4": "USB_DN", "2": "GND", "5": "+5V"}, (265, 40), mpn="USBLC6-2SC6")

# ---- 3.3 V regulator
part("U2", "Regulator_Linear:AP2112K-3.3", "AP2112K-3.3", "Package_TO_SOT_SMD:SOT-23-5",
     {"1": "+5V", "3": "+5V", "2": "GND", "5": "+3V3", "4": None}, (300, 40), mpn="AP2112K-3.3TRG1 (600 mA)")
part("C1", "Device:C", "22uF 10V", FP_C_BIG, {"1": "+5V", "2": "GND"}, (330, 40), note="bulk on the 5 V rail")
part("C2", "Device:C", "22uF 10V", FP_C_BIG, {"1": "+3V3", "2": "GND"}, (345, 40))
part("C3", "Device:C", "100nF", FP_C, {"1": "+3V3", "2": "GND"}, (360, 40))
part("D1", "Device:LED", "Power LED", "LED_SMD:LED_0805_2012Metric", {"1": "PWR_LED", "2": "GND"}, (380, 40), note="green or blue")
part("R11", "Device:R", "1k", FP_R, {"1": "+5V", "2": "PWR_LED"}, (395, 40))

# ---- reset, boot, stopwatch buttons
part("R1", "Device:R", "10k", FP_R, {"1": "+3V3", "2": "EN"}, (150, 95), note="EN pull-up")
part("C4", "Device:C", "1uF", FP_C, {"1": "EN", "2": "GND"}, (165, 95), note="EN reset delay")
part("SW1", "Switch:SW_Push", "RESET", "Button_Switch_SMD:SW_SPST_B3S-1000", {"1": "EN", "2": "GND"}, (185, 95), mpn="6x6 SMD tact switch")
part("SW2", "Switch:SW_Push", "BOOT", "Button_Switch_SMD:SW_SPST_B3S-1000", {"1": "BOOT", "2": "GND"}, (205, 95), mpn="6x6 SMD tact switch",
     note="GPIO0: hold while pressing RESET to enter the USB bootloader; firmware also uses it (WiFi setup / pairing reset)")
part("SW3", "Switch:SW_Push", "STOPWATCH", "Button_Switch_SMD:SW_SPST_B3S-1000", {"1": "STOPWATCH", "2": "GND"}, (225, 95), mpn="6x6 SMD tact switch")

part("J7", "Connector_Generic:Conn_01x02", "STOPWATCH SW", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
     {"1": "STOPWATCH", "2": "GND"}, (245, 95), note="external stopwatch push button (in parallel with SW3): pin 1 = GPIO4, pin 2 = GND")

# ---- display: 74AHCT125 level shifter (3.3 V GPIO -> 5 V MAX7219) and the 5-pin connector
part("U3", "74xx:74AHCT125", "74AHCT125", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
     {"1": "GND", "2": "MAX_DIN_3V", "3": "DISP_DIN", "4": "GND", "5": "MAX_CS_3V", "6": "DISP_CS",
      "8": "DISP_CLK", "9": "MAX_CLK_3V", "10": "GND", "11": None, "12": "GND", "13": "GND", "7": "GND", "14": "+5V"},
     (150, 150), mpn="SN74AHCT125D", note="MAX7219 needs >= 3.5 V logic-high at 5 V; the 4th gate is parked")
part("C7", "Device:C", "100nF", FP_C, {"1": "+5V", "2": "GND"}, (330, 150))
part("J2", "Connector_Generic:Conn_01x05", "DISPLAY IN", "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical",
     {"1": "+5V", "2": "GND", "3": "DISP_DIN", "4": "DISP_CS", "5": "DISP_CLK"}, (360, 150),
     note="to the MAX7219 module IN header: VCC GND DIN CS CLK (check the order on YOUR module)")

# ---- audio: MAX98357A I2S amplifier + 8 ohm speaker
_amp = {"1": "I2S_DIN", "2": None, "3": "GND", "4": "AMP_SD", "5": None, "6": None, "7": "+5V", "8": "+5V",
        "9": "SPK_P", "10": "SPK_N", "11": "GND", "12": None, "13": None, "14": "I2S_LRC", "15": "GND", "16": "I2S_BCLK",
        "17": "GND"}
part("U4", "Audio:MAX98357A", "MAX98357A", "Package_DFN_QFN:TQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm", _amp, (150, 215),
     mpn="MAX98357AETE+T (LCSC C910544)", note="GAIN_SLOT floating = 9 dB; SD_MODE high (>1.4 V) = on, mixes L+R")
part("C5", "Device:C", "10uF 10V", FP_C, {"1": "+5V", "2": "GND"}, (200, 215))
part("C6", "Device:C", "100nF", FP_C, {"1": "+5V", "2": "GND"}, (215, 215))
part("R3", "Device:R", "100k", FP_R, {"1": "+3V3", "2": "AMP_SD"}, (230, 215), note="amp on by default; GPIO15 can mute it")
part("J5", "Connector_Generic:Conn_01x02", "SPEAKER 8R 2W", "Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal",
     {"1": "SPK_P", "2": "SPK_N"}, (250, 215), mpn="JST S2B-PH-K-S",
     note="2030 cavity speaker (20x30 mm, 8 ohm, 2 W); bridge output: neither wire is ground")
part("TP1", "Connector:TestPoint", "SPK+ pad", "TestPoint:TestPoint_Pad_D2.5mm", {"1": "SPK_P"}, (275, 215), note="solder the speaker wire here instead of the JST")
part("TP2", "Connector:TestPoint", "SPK- pad", "TestPoint:TestPoint_Pad_D2.5mm", {"1": "SPK_N"}, (290, 215))

# ---- sensors and headers
part("RT1", "Device:Thermistor_NTC", "NTC 10k", FP_R06, {"1": "+3V3", "2": "NTC_ADC"}, (150, 265), mpn="10k NTC, B=3950, 0603 (e.g. NCP18XH103F03RB)")
part("R4", "Device:R", "10k", FP_R, {"1": "NTC_ADC", "2": "GND"}, (170, 265))
part("C8", "Device:C", "100nF", FP_C, {"1": "NTC_ADC", "2": "GND"}, (185, 265))
part("J6", "Connector_Generic:Conn_01x02", "LDR", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
     {"1": "+3V3", "2": "LDR_ADC"}, (205, 265), note="optional LDR (GL5528) between 3V3 and the pin")
part("R8", "Device:R", "10k", FP_R, {"1": "LDR_ADC", "2": "GND"}, (225, 265))
part("J3", "Connector_Generic:Conn_01x03", "DHT22", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
     {"1": "+3V3", "2": "DHT_DATA", "3": "GND"}, (245, 265), note="optional DHT22: VCC DATA GND (check YOUR module)")
part("R5", "Device:R", "10k", FP_R, {"1": "+3V3", "2": "DHT_DATA"}, (265, 265))
part("J4", "Connector_Generic:Conn_01x04", "I2C (RTC V2)", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
     {"1": "GND", "2": "+3V3", "3": "I2C_SCL", "4": "I2C_SDA"}, (285, 265), note="for a V2 RTC (PCF8563 / DS3231 module) or other I2C sensors")
part("R6", "Device:R", "4.7k", FP_R, {"1": "+3V3", "2": "I2C_SDA"}, (310, 265))
part("R7", "Device:R", "4.7k", FP_R, {"1": "+3V3", "2": "I2C_SCL"}, (325, 265))

# M3 holes: PLACEHOLDER positions, move them to match YOUR module's mounting holes
for i in range(1, 5):
    part(f"H{i}", "Mechanical:MountingHole", "M3", "MountingHole:MountingHole_3.2mm_M3", {}, (360 + i * 15, 265))

# ---- PCB floor plan (x right, y down, mm from the top-left corner; board 128 x 33)
PLACE = {
    "U1": (12.75, 16.5, 90),
    "U2": (31, 6, 0), "C1": (37, 6, 0), "C2": (31, 11.5, 0), "C3": (37, 11.5, 0),
    "R1": (30, 14.5, 0), "C4": (30, 19, 0),
    "SW1": (34, 27, 0), "SW2": (44, 27, 0), "SW3": (54, 27, 0), "J7": (61, 27, 0),
    "U4": (53, 12, 0), "C5": (47, 6, 0), "C6": (59, 6, 0), "R3": (47, 17, 90),
    "J5": (70, 25, 0), "TP1": (77, 27, 0), "TP2": (81, 27, 0),
    "U3": (84, 10, 90), "C7": (77, 5, 0),
    "RT1": (92, 4.5, 0), "R4": (96, 4.5, 0), "C8": (100, 4.5, 0),
    "J6": (91, 12, 0), "R8": (96, 9.5, 0),
    "J3": (98, 17, 0), "R5": (103, 9.5, 0),
    "J4": (91, 22, 0), "R6": (105, 4.5, 0), "R7": (109, 4.5, 0),
    "J1": (108, 29, 0), "U5": (98, 26, 0), "R9": (114, 22, 90), "R10": (117, 22, 90),
    "J2": (125.5, 11.42, 0),
    "D1": (113, 4.5, 0), "R11": (117, 4.5, 0),
    "H1": (23.5, 3, 0), "H2": (21, 30, 0), "H3": (125, 3, 0), "H4": (125, 30, 0),
}
for p in parts:
    p["pcb"] = PLACE[p["ref"]]

PWR_FLAG_NETS = ["GND", "+5V"]

BOARD_W, BOARD_H = 128.0, 33.0
ANT_KEEPOUT_X = 6.9     # no copper / pour / parts left of this x (ESP32-S3-MINI-1 antenna end)
GND_POUR = [(ANT_KEEPOUT_X, 0.5), (BOARD_W - 0.5, 0.5), (BOARD_W - 0.5, BOARD_H - 0.5), (ANT_KEEPOUT_X, BOARD_H - 0.5)]



# ============================================================================
# Schematic writer
# ============================================================================
def snap(v, g=1.27):
    return round(round(v / g) * g, 4)


def write_schematic():
    root = uid("root")
    items = []
    used = {}
    for p in parts:
        used[p["lib_id"]] = True
    used["power:PWR_FLAG"] = True

    def label(net, x, y, angle, key):
        just = {0: "left", 180: "right", 90: "left", 270: "right"}[angle]
        items.append(["global_label", Q(net), ["shape", "passive"], ["at", x, y, angle], ["fields_autoplaced", "yes"],
                      ["effects", ["font", ["size", 1.27, 1.27]], ["justify"] + just.split()[:1]],
                      ["uuid", Q(uid("lbl", key))],
                      ["property", Q("Intersheetrefs"), Q("${INTERSHEET_REFS}"), ["at", x, y, 0], ["hide", "yes"],
                       ["effects", ["font", ["size", 1.27, 1.27]]]]])

    def wire(x1, y1, x2, y2, key):
        items.append(["wire", ["pts", ["xy", x1, y1], ["xy", x2, y2]], ["stroke", ["width", 0], ["type", "default"]],
                      ["uuid", Q(uid("w", key))]])

    def noconn(x, y, key):
        items.append(["no_connect", ["at", x, y], ["uuid", Q(uid("nc", key))]])

    def place(ref, lib_id, value, fp, pins, X, Y, unit, key):
        units = symbol_pins(lib_id)
        pinlist = units.get(0, []) + units.get(unit, [])
        props = [
            ["property", Q("Reference"), Q(ref), ["at", X + 2.54, Y - 5.08, 0], ["effects", ["font", ["size", 1.27, 1.27]], ["justify", "left"]]],
            ["property", Q("Value"), Q(value), ["at", X + 2.54, Y + 5.08, 0], ["effects", ["font", ["size", 1.27, 1.27]], ["justify", "left"]]],
            ["property", Q("Footprint"), Q(fp or ""), ["at", X, Y, 0], ["hide", "yes"], ["effects", ["font", ["size", 1.27, 1.27]]]],
            ["property", Q("Datasheet"), Q(""), ["at", X, Y, 0], ["hide", "yes"], ["effects", ["font", ["size", 1.27, 1.27]]]],
        ]
        sym = ["symbol", ["lib_id", Q(lib_id)], ["at", X, Y, 0], ["unit", unit],
               ["exclude_from_sim", "no"], ["in_bom", "no" if lib_id.startswith(("power:", "Mechanical:")) else "yes"],
               ["on_board", "no" if lib_id.startswith("power:") else "yes"], ["dnp", "no"],
               ["uuid", Q(uid("sym", key))]] + props
        for num, *_ in pinlist:
            sym.append(["pin", Q(num), ["uuid", Q(uid("pin", key, num))]])
        sym.append(["instances", ["project", Q(NAME), ["path", Q("/" + root), ["reference", Q(ref)], ["unit", unit]]]])
        items.append(sym)
        for num, px, py, ang, ptype in pinlist:
            x0, y0 = X + px, Y - py
            dx, dy = -math.cos(math.radians(ang)), math.sin(math.radians(ang))
            dx, dy = round(dx), round(dy)
            net = pins.get(num, "__missing__")
            if net == "__missing__" or net is None:
                if ptype != "no_connect":
                    noconn(x0, y0, f"{key}.{num}")
                continue
            x1, y1 = round(x0 + dx * 2.54, 4), round(y0 + dy * 2.54, 4)
            wire(x0, y0, x1, y1, f"{key}.{num}")
            angle = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[(dx, dy)]
            label(net, x1, y1, angle, f"{key}.{num}")
        return sym

    for p in parts:
        X, Y = snap(p["sch"][0], 2.54), snap(p["sch"][1], 2.54)
        units = sorted(u for u in symbol_pins(p["lib_id"]) if u > 0) or [1]
        for k, u in enumerate(units):
            place(p["ref"], p["lib_id"], p["value"], p["fp"], p["pins"], X + k * 33.02, Y, u, f"{p['ref']}.{u}")
        p["sch_uuid"] = uid("sym", f"{p['ref']}.{units[0]}")

    for i, net in enumerate(PWR_FLAG_NETS):
        X, Y = snap(300 + i * 12.7, 2.54), snap(170 - 25, 2.54)
        place(f"#FLG{i + 1:02d}", "power:PWR_FLAG", "PWR_FLAG", "", {"1": net}, X, Y, 1, f"FLG{i}")


    notes = [
        (150, 28, "POWER: USB-C 5 V -> AP2112K 3.3 V. CC1/CC2 5.1k pull-downs, USBLC6 on D+/D-"),
        (20, 80, "ESP32-S3-MINI-1-N8. GPIO0 BOOT / GPIO4 STOPWATCH / GPIO1 LDR / GPIO10-12 SPI as in firmware config.h"),
        (150, 80, "RESET / BOOT / STOPWATCH buttons"),
        (150, 135, "DISPLAY: 74AHCT125 shifts 3.3 V SPI to 5 V for the MAX7219 module (VCC GND DIN CS CLK)"),
        (150, 200, "AUDIO: MAX98357A I2S amplifier, BCLK GPIO5 / LRC GPIO6 / DIN GPIO7, SD GPIO15, 8 ohm speaker"),
        (150, 250, "SENSORS: NTC GPIO2, LDR GPIO1, DHT22 GPIO13, I2C SDA GPIO8 / SCL GPIO9 (RTC in V2)"),
    ]
    for i, (x, y, t) in enumerate(notes):
        items.append(["text", Q(t), ["exclude_from_sim", "no"], ["at", x, y, 0],
                      ["effects", ["font", ["size", 2, 2], ["bold", "yes"]], ["justify", "left", "bottom"]],
                      ["uuid", Q(uid("note", i))]])

    sch = ["kicad_sch", ["version", 20250114], ["generator", Q("eeschema")], ["generator_version", Q("9.0")],
           ["uuid", Q(root)], ["paper", Q("A3")],
           ["title_block", ["title", Q("DotGlow V1 board - ESP32-S3 + MAX7219 4-in-1, USB-C, speaker")], ["date", Q("2026-10-18")],
            ["rev", Q("1.0")], ["company", Q("ElectroIoT")],
            ["comment", 1, Q("Generated by hardware/generate_kicad.py - edit the script, not this file")]],
           ["lib_symbols"] + [embedded_symbol(l) for l in sorted(used)]]
    sch += items
    sch.append(["sheet_instances", ["path", Q("/"), ["page", Q("1")]]])
    open(os.path.join(OUT, NAME + ".kicad_sch"), "w", encoding="utf-8").write(dump(sch) + "\n")


# ============================================================================
# Project files
# ============================================================================
def write_project_files():
    open(os.path.join(OUT, "fp-lib-table"), "w").write("(fp_lib_table\n\t(version 7)\n)\n")
    open(os.path.join(OUT, "sym-lib-table"), "w").write("(sym_lib_table\n\t(version 7)\n)\n")
    cls = lambda name, tw, via, vd, pr: {
        "name": name, "clearance": 0.15, "track_width": tw, "via_diameter": via, "via_drill": vd,
        "diff_pair_gap": 0.25, "diff_pair_width": 0.2, "microvia_diameter": 0.3, "microvia_drill": 0.1,
        "wire_width": 6, "bus_width": 12, "line_style": 0, "schematic_color": "rgba(0, 0, 0, 0.000)",
        "pcb_color": "rgba(0, 0, 0, 0.000)", "priority": pr}
    pro = {
        "meta": {"filename": NAME + ".kicad_pro", "version": 3},
        "board": {"design_settings": {"defaults": {}, "rules": {"min_clearance": 0.15, "min_track_width": 0.2, "min_via_diameter": 0.5, "min_through_hole_diameter": 0.3, "min_hole_clearance": 0.2, "min_hole_to_hole": 0.25, "min_copper_edge_clearance": 0.3, "min_silk_clearance": 0.0}}},
        "net_settings": {
            "classes": [cls("Default", 0.3, 0.6, 0.3, 2147483647), cls("Power", 0.6, 0.8, 0.4, 1)],
            "meta": {"version": 4},
            "netclass_patterns": [{"netclass": "Power", "pattern": p} for p in ("+5V", "VIN_*", "GND", "BUZ_C")],
        },
    }
    json.dump(pro, open(os.path.join(OUT, NAME + ".kicad_pro"), "w"), indent=2)


# ============================================================================
# PCB writer (pcbnew API)
# ============================================================================
def schematic_nc_nets():
    """(ref, pad) -> 'unconnected-(...)' net names, read from KiCad's own netlist export."""
    import subprocess, tempfile
    cli = os.path.join(os.path.dirname(KICAD), "..", "bin", "kicad-cli.exe")
    tmp = os.path.join(tempfile.gettempdir(), "tg_nc.net")
    subprocess.run([os.path.normpath(cli), "sch", "export", "netlist", "--format", "kicadsexpr", "-o", tmp,
                    os.path.join(OUT, NAME + ".kicad_sch")], check=True, capture_output=True)
    out = {}
    for n in find(first(parse(open(tmp, encoding="utf-8").read()), "nets"), "net"):
        name = first(n, "name")[1]
        if name.startswith("unconnected-"):
            for nd in find(n, "node"):
                out[(first(nd, "ref")[1], first(nd, "pin")[1])] = name
    return out


def write_pcb():
    import pcbnew
    nc_nets = schematic_nc_nets()
    mm = pcbnew.FromMM
    V = lambda x, y: pcbnew.VECTOR2I(mm(x + OX), mm(y + OY))
    OX, OY = 50.0, 50.0

    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    # fab origin = bottom-left board corner (JLCPCB-friendly CPL coordinates)
    board.GetDesignSettings().SetAuxOrigin(V(0, BOARD_H))
    board.GetDesignSettings().SetGridOrigin(V(0, BOARD_H))
    nets = {}

    def net(name):
        if name not in nets:
            ni = pcbnew.NETINFO_ITEM(board, name)
            board.Add(ni)
            nets[name] = ni
        return nets[name]

    for p in parts:
        lib, fpname = p["fp"].split(":")
        libpath = os.path.join(KICAD, "footprints", lib + ".pretty")
        fp = pcbnew.FootprintLoad(libpath, fpname)
        if fp is None:
            raise SystemExit(f"footprint not found: {p['fp']}")
        fp.SetFPID(pcbnew.LIB_ID(lib, fpname))
        fp.SetReference(p["ref"])
        fp.SetValue(p["value"])
        fp.SetPath(pcbnew.KIID_PATH("/" + p["sch_uuid"]))
        x, y, rot = p["pcb"]
        fp.SetPosition(V(x, y))
        fp.SetOrientationDegrees(rot)
        for item in list(fp.GraphicalItems()):
            if item.GetLayer() == pcbnew.Edge_Cuts:   # jack footprints carry a "PCB edge" marker
                item.SetLayer(pcbnew.Dwgs_User)
        fp.SetExcludedFromBOM(p["lib_id"].startswith("Mechanical:"))
        for pad in fp.Pads():
            n = p["pins"].get(pad.GetNumber()) or nc_nets.get((p["ref"], pad.GetNumber()))
            if n:
                pad.SetNet(net(n))
        board.Add(fp)

    # Board outline
    def seg(x1, y1, x2, y2, layer=pcbnew.Edge_Cuts, w=0.1):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(x1, y1))
        s.SetEnd(V(x2, y2))
        s.SetLayer(layer)
        s.SetWidth(mm(w))
        board.Add(s)

    for a, b in [((0, 0), (BOARD_W, 0)), ((BOARD_W, 0), (BOARD_W, BOARD_H)),
                 ((BOARD_W, BOARD_H), (0, BOARD_H)), ((0, BOARD_H), (0, 0))]:
        seg(*a, *b)


    # Silkscreen
    def text(t, x, y, size=1.5, layer=pcbnew.F_SilkS):
        tx = pcbnew.PCB_TEXT(board)
        tx.SetText(t)
        tx.SetPosition(V(x, y))
        tx.SetLayer(layer)
        tx.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
        tx.SetTextThickness(mm(size * 0.15))
        board.Add(tx)

    text("DOTGLOW V1", 68, 17, 1.4)
    text("ElectroIoT.in", 68, 20, 1.0)
    text("RST", 34, 31.2, 0.8)
    text("BOOT", 44, 31.2, 0.8)
    text("STOP", 54, 31.2, 0.8)
    text("SW", 61.5, 31.8, 0.7)
    text("SPK", 70, 31.5, 0.8)
    text("DISPLAY", 118, 28.5, 0.8)
    text("ANT", 2.5, 3, 0.8)

    # antenna keep-out: no copper, tracks, vias or footprints left of ANT_KEEPOUT_X
    ko = pcbnew.ZONE(board)
    ko.SetIsRuleArea(True)
    ko.SetLayerSet(pcbnew.LSET.AllCuMask())
    ko.SetDoNotAllowZoneFills(True)
    ko.SetDoNotAllowTracks(True)
    ko.SetDoNotAllowVias(True)
    ko.SetDoNotAllowPads(False)
    ko.SetDoNotAllowFootprints(False)
    ko.SetZoneName("ESP32 antenna keep-out")
    ol = ko.Outline()
    ol.NewOutline()
    for (x, y) in [(0, 0), (ANT_KEEPOUT_X, 0), (ANT_KEEPOUT_X, BOARD_H), (0, BOARD_H)]:
        ol.Append(mm(x + OX), mm(y + OY))
    board.Add(ko)

    # GND pour on both layers, low-voltage area only (mains area + slots excluded).
    # route_pcb.py sets TG_NO_ZONES=1 and pours after autorouting instead.
    for layer in (() if os.environ.get("TG_NO_ZONES") else (pcbnew.F_Cu, pcbnew.B_Cu)):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(net("GND"))
        z.SetLocalClearance(mm(0.3))
        z.SetMinThickness(mm(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        ol = z.Outline()
        ol.NewOutline()
        for (x, y) in GND_POUR:
            ol.Append(mm(x + OX), mm(y + OY))
        board.Add(z)

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.SetFileName(os.path.join(OUT, NAME + ".kicad_pcb"))
    pcbnew.SaveBoard(os.path.join(OUT, NAME + ".kicad_pcb"), board)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    write_project_files()
    write_schematic()
    try:
        write_pcb()
        print("PCB written")
    except ImportError:
        print("pcbnew not available - run with KiCad's python.exe to also generate the PCB")
    print("parts:", len(parts), "nets:", len({n for p in parts for n in p["pins"].values() if n}))
