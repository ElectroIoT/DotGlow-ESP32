"""
Tiny built-in grid router for the DotGlow V1 board (2 layers, Manhattan tracks, vias).
No external autorouter needed. Run with KiCad's python after generate_kicad.py:

    set TG_NO_ZONES=1
    "%LOCALAPPDATA%/Programs/KiCad/10.0/bin/python.exe" hardware/pcb/generate_kicad.py
    "%LOCALAPPDATA%/Programs/KiCad/10.0/bin/python.exe" hardware/pcb/route_pcb.py

Routes every net except GND with A* on a 0.25 mm grid (conservative square clearance), then pours GND
on both layers. Overwrites the .kicad_pcb. Edit the board by hand only after the last run.
"""
import heapq
import os
import sys

import numpy as np
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "kicad", "dotglow-v1.kicad_pcb")
sys.path.insert(0, HERE)
from generate_kicad import GND_POUR, BOARD_W, BOARD_H, ANT_KEEPOUT_X  # noqa: E402

OX, OY = 50.0, 50.0           # page offset used by generate_kicad.py
G = 0.05                      # grid, mm (fine: the MAX98357A QFN has 0.5 mm pitch)
CLR = 0.15                    # clearance, mm (JLCPCB can do 0.127)
TRACK = 0.2                   # normal track width, mm
WTRACK = 0.4                  # wide track (power, speaker)
MARGIN = TRACK / 2 + CLR + G / 2   # half track + clearance + half grid
VIA_D, VIA_DRILL = 0.6, 0.3
VIA_R = int(round((VIA_D / 2 + CLR + TRACK / 2 + G / 2) / G)) + 1   # cells kept clear around a placed via
VIA_DIL = 4                   # extra cells kept free around a via centre
mm = pcbnew.FromMM
tomm = pcbnew.ToMM

board = pcbnew.LoadBoard(PCB)
W, H = int(BOARD_W / G) + 1, int(BOARD_H / G) + 1
own = [np.zeros((H, W), dtype=np.int16) for _ in range(2)]   # 0 free, k = net id, -1 = blocked


def cell(x, y):
    return int(round(x / G)), int(round(y / G))


def mark(layer, x0, y0, x1, y1, k, margin):
    cx0, cy0 = cell(x0 - margin, y0 - margin)
    cx1, cy1 = cell(x1 + margin, y1 + margin)
    cx0, cy0 = max(cx0, 0), max(cy0, 0)
    cx1, cy1 = min(cx1, W - 1), min(cy1, H - 1)
    if cx1 < cx0 or cy1 < cy0:
        return
    a = own[layer][cy0:cy1 + 1, cx0:cx1 + 1]
    a[(a == 0)] = k
    a[(a != 0) & (a != k)] = -1


netid = {}


def nid(name):
    if not name:
        return -1
    return netid.setdefault(name, len(netid) + 1)


gnd = {}
pads = {}        # net name -> list of (ref, num, x, y, layers)
padcells = {}    # net id -> {(layer, cx, cy)}
for fp in board.GetFootprints():
    for pad in fp.Pads():
        bb = pad.GetBoundingBox()
        x0, y0, x1, y1 = (tomm(bb.GetLeft()) - OX, tomm(bb.GetTop()) - OY, tomm(bb.GetRight()) - OX, tomm(bb.GetBottom()) - OY)
        name = pad.GetNetname()
        k = nid(name)
        thru = pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
        layers = [0, 1] if thru else [0]
        if fp.GetReference() == "U1" and pad.GetNumber() == "61":
            layers = [0, 1]   # keep tracks off the back side under the thermal vias
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            k = -1
        for l in layers:
            mark(l, x0, y0, x1, y1, k, MARGIN + (0.1 if k == -1 else 0.0))
        if k > 0:
            c = pad.GetPosition()
            px, py = tomm(c.x) - OX, tomm(c.y) - OY
            if name != "GND":
                pads.setdefault(name, []).append((fp.GetReference(), pad.GetNumber(), px, py, layers))
            else:
                gnd[(fp.GetReference(), pad.GetNumber())] = (fp.GetReference(), pad.GetNumber(), px, py, layers)
        if k > 0:
            cx0, cy0 = cell(x0, y0)
            cx1, cy1 = cell(x1, y1)
            for l in layers:
                for cy in range(cy0, cy1 + 1):
                    for cx in range(cx0, cx1 + 1):
                        padcells.setdefault(k, set()).add((l, cx, cy))

# board edge keepout
e = int(0.6 / G) + 1
for l in (0, 1):
    own[l][:e, :] = -1
    own[l][-e:, :] = -1
    own[l][:, :e] = -1
    own[l][:, -e:] = -1

kx = int(ANT_KEEPOUT_X / G)
for l in (0, 1):
    own[l][:, :kx] = -1

WIDE = {"+5V", "+3V3"}
MID = {"SPK_P", "SPK_N"}      # 0.3 mm: ~0.7 A, fine for a 2 W speaker and still fits the 0.5 mm QFN pitch
ORDER = ["USB_DP", "USB_DN", "CC1", "CC2", "SPK_P", "SPK_N", "I2S_BCLK", "I2S_LRC", "I2S_DIN", "AMP_SD",
         "MAX_DIN_3V", "MAX_CS_3V", "MAX_CLK_3V", "DISP_DIN", "DISP_CS", "DISP_CLK", "EN", "BOOT", "STOPWATCH",
         "I2C_SDA", "I2C_SCL", "NTC_ADC", "LDR_ADC", "DHT_DATA", "PWR_LED", "+5V", "+3V3"]
for n in pads:
    if n not in ORDER:
        ORDER.append(n)
# GND is poured; pads that the pour cannot reach are linked to a pad that it does reach
GND_LINKS = []
# GND pads outside the ESP32 module are tied to the rest of the ground with real tracks (the pour alone leaves islands)
gnd_pads = [v for key, v in gnd.items() if key[0] != "U1"]
if len(gnd_pads) >= 2:
    pads["GND"] = gnd_pads
    ORDER.append("GND")
for i, (a, b) in enumerate(GND_LINKS):
    key = f"GND#{i}"
    pads[key] = [gnd[a], gnd[b]]
    netid[key] = netid["GND"]
    ORDER.append(key)

tracks = []   # (net, layer, x1, y1, x2, y2, width)
vias = []     # (net, x, y)


def dilate(m):
    d = m.copy()
    d[1:, :] |= m[:-1, :]
    d[:-1, :] |= m[1:, :]
    d[:, 1:] |= m[:, :-1]
    d[:, :-1] |= m[:, 1:]
    return d


def route_net(name):
    k = netid[name]
    width = WTRACK if name in WIDE else (0.3 if name in MID else TRACK)
    wide = width > TRACK
    extra = int(round((width - TRACK) / 2 / G))
    blocked = []
    for l in (0, 1):
        b = (own[l] != 0) & (own[l] != k)
        if wide:
            for _ in range(extra):
                b = dilate(b)
        blocked.append(b)
    for (l, cx, cy) in padcells.get(k, ()):
        if 0 <= cx < W and 0 <= cy < H:
            blocked[l][cy, cx] = False
    via_block = []
    for b in blocked:
        v = b
        for _ in range(VIA_DIL):
            v = dilate(v)
        via_block.append(v)
    plist = pads[name]
    if len(plist) < 2:
        return True

    def pad_cells(p):
        c = cell(p[2], p[3])
        return [(l, c[0], c[1]) for l in p[4]]

    tree = set(pad_cells(plist[0]))
    remaining = list(plist[1:])
    while remaining:
        # closest remaining pad to the tree (by pad centre distance)
        tx = [(c[1], c[2]) for c in tree]
        def dist(p):
            cx, cy = cell(p[2], p[3])
            return min(abs(cx - a) + abs(cy - b) for a, b in tx)
        remaining.sort(key=dist)
        p = remaining.pop(0)
        starts = pad_cells(p)
        xs = [c[1] for c in tree]
        ys = [c[2] for c in tree]
        bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)

        def h(cx, cy):
            dx = max(bx0 - cx, 0, cx - bx1)
            dy = max(by0 - cy, 0, cy - by1)
            return dx + dy

        pq = []
        best = {}
        prev = {}
        for s in starts:
            best[s] = 0
            heapq.heappush(pq, (h(s[1], s[2]), 0, s, None))
        goal = None
        while pq:
            f, g, cur, pd = heapq.heappop(pq)
            if best.get(cur, 1e18) < g:
                continue
            if cur in tree:
                goal = cur
                break
            l, cx, cy = cur
            moves = []
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < W and 0 <= ny < H and not blocked[l][ny, nx]:
                    moves.append(((l, nx, ny), 1.0 + (0.4 if pd and pd != (dx, dy) else 0.0) + (0.15 if (l == 0) != (dx != 0) else 0.0), (dx, dy)))
            if not via_block[0][cy, cx] and not via_block[1][cy, cx]:
                moves.append(((1 - l, cx, cy), 12.0, None))
            for nxt, cost, d in moves:
                ng = g + cost
                if ng < best.get(nxt, 1e18):
                    best[nxt] = ng
                    prev[nxt] = cur
                    heapq.heappush(pq, (ng + h(nxt[1], nxt[2]), ng, nxt, d))
        if goal is None:
            print("  FAILED to connect", name, p[0], p[1])
            return False
        path = [goal]
        while path[-1] in prev and path[-1] not in starts:
            path.append(prev[path[-1]])
        path.reverse()
        # emit geometry
        i = 0
        while i < len(path) - 1:
            a, b = path[i], path[i + 1]
            if a[0] != b[0]:
                vias.append((name, a[1] * G, a[2] * G))
                i += 1
                continue
            j = i + 1
            dx, dy = b[1] - a[1], b[2] - a[2]
            while j + 1 < len(path) and path[j + 1][0] == a[0] and (path[j + 1][1] - path[j][1], path[j + 1][2] - path[j][2]) == (dx, dy):
                j += 1
            e_ = path[j]
            tracks.append((name, a[0], a[1] * G, a[2] * G, e_[1] * G, e_[2] * G, width))
            i = j
        # mark copper in the occupancy maps
        r = int(round(MARGIN / G)) + (extra if wide else 0)
        for (l, cx, cy) in path:
            a = own[l][max(cy - r, 0):cy + r + 1, max(cx - r, 0):cx + r + 1]
            a[(a == 0)] = k
            a[(a != 0) & (a != k)] = -1
        for (n_, vx, vy) in vias:
            if n_ == name:
                cx, cy = cell(vx, vy)
                for l in (0, 1):
                    a = own[l][max(cy - VIA_R, 0):cy + VIA_R + 1, max(cx - VIA_R, 0):cx + VIA_R + 1]
                    a[(a == 0)] = k
                    a[(a != 0) & (a != k)] = -1
        tree |= set(path)
        tree |= set(starts)
        for s in starts:
            padcells.setdefault(k, set()).add(s)
    return True


import copy
own0 = [a.copy() for a in own]
padcells0 = copy.deepcopy(padcells)
best = None
order = [n for n in ORDER if n in pads]
for attempt in range(int(os.environ.get("ROUTE_TRIES", "6"))):
    own = [a.copy() for a in own0]
    padcells = copy.deepcopy(padcells0)
    tracks.clear()
    vias.clear()
    failed = []
    for name in order:
        print("attempt", attempt, "routing", name, len(pads[name]), "pads", flush=True)
        if not route_net(name):
            failed.append(name)
    print("attempt", attempt, "failed:", failed, flush=True)
    if best is None or len(failed) < len(best[0]):
        best = (list(failed), list(tracks), list(vias), [a.copy() for a in own])
    if not failed:
        break
    order = failed + [n for n in order if n not in failed]
failed, tr, vi, own = best
tracks.clear()
tracks.extend(tr)
vias.clear()
vias.extend(vi)

# ---- GND stitching vias: tie the top and bottom pours together wherever there is room ----------
kg = netid["GND"]
# thermal vias in the nine centre ground pads of the ESP32 module (pad 61)
fpU1 = board.FindFootprintByReference("U1")
for pad in fpU1.Pads():
    if pad.GetNumber() == "61":
        c = pad.GetPosition()
        vias.append(("GND", tomm(c.x) - OX, tomm(c.y) - OY))
holes = []
for fp in board.GetFootprints():
    for pad in fp.Pads():
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            c = pad.GetPosition()
            holes.append((tomm(c.x) - OX, tomm(c.y) - OY))
gb = [(own[l] != 0) & (own[l] != kg) for l in (0, 1)]
stitch = []
for yy in range(3, int(BOARD_H) - 2, 3):
    for xx in range(3, int(BOARD_W) - 2, 3):
        if xx < ANT_KEEPOUT_X + 1:
            continue
        cx, cy = cell(xx, yy)
        if any(abs(vx - xx) < 1.0 and abs(vy - yy) < 1.0 for (_, vx, vy) in vias):
            continue
        if any((xx - hx) ** 2 + (yy - hy) ** 2 < 2.4 ** 2 for hx, hy in holes):
            continue
        clear = True
        for l in (0, 1):
            win = own[l][cy - VIA_R:cy + VIA_R + 1, cx - VIA_R:cx + VIA_R + 1]
            if np.any((win != 0) & (win != kg)):
                clear = False
        if clear:
            stitch.append((xx, yy))
            vias.append(("GND", xx, yy))
            for l in (0, 1):
                own[l][cy - 11:cy + 12, cx - 11:cx + 12] = np.where(own[l][cy - 11:cy + 12, cx - 11:cx + 12] == 0, kg, own[l][cy - 11:cy + 12, cx - 11:cx + 12])
print("stitching vias", len(stitch))

# ---- write tracks, vias, GND pour -----------------------------------------------------------
layer_of = (pcbnew.F_Cu, pcbnew.B_Cu)
for (name, l, x1, y1, x2, y2, w) in tracks:
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(mm(x1 + OX), mm(y1 + OY)))
    t.SetEnd(pcbnew.VECTOR2I(mm(x2 + OX), mm(y2 + OY)))
    t.SetWidth(mm(w))
    t.SetLayer(layer_of[l])
    t.SetNet(board.FindNet(name.split("#")[0]))
    board.Add(t)
for (name, x, y) in vias:
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(mm(x + OX), mm(y + OY)))
    v.SetWidth(mm(VIA_D))
    v.SetDrill(mm(VIA_DRILL))
    v.SetNet(board.FindNet(name.split("#")[0]))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(v)

for layer in layer_of:
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(board.FindNet("GND"))
    z.SetLocalClearance(mm(0.3))
    z.SetMinThickness(mm(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in GND_POUR:
        ol.Append(mm(x + OX), mm(y + OY))
    board.Add(z)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print("tracks", len(tracks), "vias", len(vias), "failed", failed)
print("saved", PCB)
