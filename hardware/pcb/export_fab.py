"""
Export the manufacturing files into hardware/fab and pictures into hardware/renders (KiCad 10 CLI).

    python hardware/export_fab.py           (plain python 3 is enough, it calls kicad-cli)
"""
import csv
import glob
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
KDIR = os.path.join(HERE, "kicad")
NAME = "dotglow-v1"
PCB = os.path.join(KDIR, NAME + ".kicad_pcb")
SCH = os.path.join(KDIR, NAME + ".kicad_sch")
FAB = os.path.join(HERE, "fab")
GER = os.path.join(FAB, "gerbers")
REN = os.path.join(HERE, "renders")
KBIN = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs/KiCad/10.0/bin")
if not os.path.isdir(KBIN):
    KBIN = "C:/Program Files/KiCad/10.0/bin"
CLI = KBIN + "/kicad-cli.exe"
PY = KBIN + "/python.exe"


def run(*a):
    r = subprocess.run([CLI, *a], capture_output=True, text=True)
    if r.returncode:
        print(r.stdout, r.stderr)
        sys.exit(1)


# KiCad rewrites the .kicad_pro with defaults: put the design rules the board was routed with back
import json  # noqa: E402
_pro = os.path.join(KDIR, NAME + ".kicad_pro")
_j = json.load(open(_pro, encoding="utf-8"))
for _c in _j["net_settings"]["classes"]:
    _c["clearance"] = 0.15
    _c["track_width"] = 0.2
_r = _j["board"]["design_settings"]["rules"]
_r.update({"min_clearance": 0.15, "min_copper_edge_clearance": 0.3, "min_hole_clearance": 0.2, "min_track_width": 0.2})
json.dump(_j, open(_pro, "w", encoding="utf-8"), indent=2)

for d in (FAB, GER, REN):
    os.makedirs(d, exist_ok=True)
for f in glob.glob(os.path.join(GER, "*")):
    os.remove(f)

# gerbers + drill (JLCPCB: protel extensions, no Protel-style X2 attributes surprises)
run("pcb", "export", "gerbers", "-o", GER + "/", "--layers",
    "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts",
    "--subtract-soldermask", "--use-drill-file-origin", PCB)
run("pcb", "export", "drill", "-o", GER + "/", "--format", "excellon", "--drill-origin", "plot",
    "--excellon-units", "mm", "--generate-map", "--map-format", "gerberx2", PCB)

# BOM (grouped) and CPL (JLCPCB column names)
sys.path.insert(0, HERE)
os.environ["TG_NO_ZONES"] = "1"
from generate_kicad import parts  # noqa: E402

groups = {}
for p in parts:
    if p["lib_id"].startswith("Mechanical:"):
        continue
    key = (p["value"], p["fp"], p["mpn"])
    groups.setdefault(key, []).append(p["ref"])
with open(os.path.join(FAB, "dotglow-v1-bom.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Comment", "Designator", "Footprint", "Qty", "Suggested part / note"])
    for (val, fp, mpn), refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
        w.writerow([val, ",".join(sorted(refs)), fp.split(":")[1], len(refs), mpn])

pos = os.path.join(FAB, "_pos.csv")
run("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "--use-drill-file-origin", "-o", pos, PCB)
with open(pos, newline="", encoding="utf-8") as f, open(os.path.join(FAB, "dotglow-v1-cpl.csv"), "w", newline="", encoding="utf-8") as o:
    rd = csv.DictReader(f)
    w = csv.writer(o)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for r in rd:
        if r["Ref"].startswith("H"):
            continue
        w.writerow([r["Ref"], r["PosX"], r["PosY"], "Top" if r["Side"] == "top" else "Bottom", r["Rot"]])
os.remove(pos)

# zips
with zipfile.ZipFile(os.path.join(FAB, "dotglow-v1-gerbers-jlcpcb.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(glob.glob(os.path.join(GER, "*"))):
        if not f.endswith(("job.gbrjob",)):
            z.write(f, os.path.basename(f))
with zipfile.ZipFile(os.path.join(FAB, "dotglow-v1-kicad-project.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(glob.glob(os.path.join(KDIR, NAME + ".*"))) + [os.path.join(KDIR, "fp-lib-table"), os.path.join(KDIR, "sym-lib-table")]:
        if f.endswith((".kicad_pcb", ".kicad_sch", ".kicad_pro", "-table")):
            z.write(f, os.path.basename(f))
    z.write(os.path.join(HERE, "generate_kicad.py"), "generate_kicad.py")
    z.write(os.path.join(HERE, "route_pcb.py"), "route_pcb.py")

# renders and reports
run("pcb", "render", "--side", "top", "--width", "3600", "--height", "1100", "--zoom", "5", "-o", os.path.join(REN, "pcb_top.png"), PCB)
run("pcb", "render", "--side", "bottom", "--width", "3600", "--height", "1100", "--zoom", "5", "-o", os.path.join(REN, "pcb_bottom.png"), PCB)
run("sch", "export", "pdf", "-o", os.path.join(REN, "schematic.pdf"), SCH)
run("pcb", "drc", "--severity-all", "--schematic-parity", "--format", "report", "-o", os.path.join(KDIR, "drc.rpt"), PCB)
run("sch", "erc", "--severity-all", "-o", os.path.join(KDIR, "erc.rpt"), SCH)
print("done:", sorted(os.listdir(FAB)), sorted(os.listdir(REN)))
