#!/usr/bin/env python3
"""DotGlow Flasher: install DotGlow firmware on an ESP32, ESP32-S3 or ESP8266 board from a PC.

    python dotglow_flasher.py                      window (pick the board, press Install)
    python dotglow_flasher.py list                 list serial ports
    python dotglow_flasher.py detect --port COM5   chip, MAC, flash size
    python dotglow_flasher.py flash  --port COM5   download the latest firmware and install it
        --update          keep WiFi / settings (only the app), ESP32 / ESP32-S3 already running DotGlow
        --file my.bin [--addr 0x0]   flash your own .bin instead
        --yes             no questions

The firmware list comes from CATALOG_URL (the same file the DotGlow phone app uses).
"""
import argparse
import hashlib
import io
import json
import os
import queue
import re
import struct
import sys
import tempfile
import threading
import time
import urllib.request

import serial.tools.list_ports

try:
    import esptool
except ImportError:                                            # pragma: no cover
    esptool = None

VERSION = "1.0.0"
CATALOG_URL = "https://manoranjan.dev/dotglow/firmware.json"
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".dotglow-flasher", "cache")
ESP_VIDS = {0x1A86: "CH340", 0x10C4: "CP210x", 0x303A: "Espressif USB", 0x0403: "FTDI"}
APP_OFFSET = 0x10000          # app0 in the DotGlow partition table (min_spiffs)
OTADATA = (0xE000, 0x2000)    # erased on an update so the boot goes to app0

# chip name printed by esptool -> catalog board key
CHIPS = {"ESP32-S3": "esp32s3", "ESP32-S2": None, "ESP32-C2": None, "ESP32-C3": None, "ESP32-C5": None,
         "ESP32-C6": None, "ESP32-H2": None, "ESP32-P4": None, "ESP8266": "esp8266",
         "ESP32": "esp32"}   # last: every other ESP32 name (D0WD, PICO, U4WDH ...) is the classic ESP32


# ---------------------------------------------------------------- serial ports

def list_ports():
    """[(device, description, likely_esp)], likely ESP boards first."""
    out = []
    for p in serial.tools.list_ports.comports():
        likely = p.vid in ESP_VIDS
        desc = p.description or p.device
        if likely and ESP_VIDS[p.vid].lower() not in desc.lower():
            desc += f" [{ESP_VIDS[p.vid]}]"
        out.append((p.device, desc, likely))
    out.sort(key=lambda t: (not t[2], t[0]))
    return out


# ---------------------------------------------------------------- esptool wrapper

class _Tee(io.TextIOBase):
    def __init__(self, cb):
        self.cb = cb

    def write(self, s):
        if s:
            self.cb(s)
        return len(s)

    def flush(self):
        pass


def run_esptool(args, on_text):
    """Run esptool in-process, feed everything it prints to on_text(str). Returns the exit code."""
    if esptool is None:
        on_text("esptool is not installed (pip install esptool)\n")
        return 1
    old = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = _Tee(on_text)
    code = 0
    try:
        esptool.main([str(a) for a in args])
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code in (None, 0) else 1)
    except Exception as e:                                       # noqa: BLE001
        on_text(f"\nError: {e}\n")
        code = 1
    finally:
        sys.stdout, sys.stderr = old
    return code


def esptool_text(args):
    buf = []
    code = run_esptool(args, buf.append)
    return code, "".join(buf)


def detect(port, baud=115200):
    """-> dict(chip, board, mac, flash, text, ok)"""
    code, text = esptool_text(["--port", port, "--baud", baud, "flash-id"])
    chip = re.search(r"Chip type:\s*(.+)", text) or re.search(r"Connected to (.+?) on", text)
    mac = re.search(r"MAC:\s*([0-9a-f:]{17})", text)
    flash = re.search(r"Detected flash size:\s*(\S+)", text)
    name = chip.group(1).strip() if chip else ""
    board = None
    for key, val in CHIPS.items():
        if name.upper().startswith(key):
            board = val
            break
    return {"ok": bool(chip) and code == 0, "chip": name, "board": board, "mac": mac.group(1) if mac else "",
            "flash": flash.group(1) if flash else "?", "text": text}


def has_dotglow_layout(port, baud, on_text=lambda s: None):
    """True when the partition table on the board has an app at APP_OFFSET (so an app-only update is safe)."""
    path = os.path.join(tempfile.gettempdir(), "dotglow_ptable.bin")
    if run_esptool(["--port", port, "--baud", baud, "read-flash", "0x8000", "0xC00", path], on_text) != 0:
        return False
    try:
        data = open(path, "rb").read()
    except OSError:
        return False
    for i in range(0, len(data) - 32, 32):
        magic, ptype, sub, off, size = struct.unpack_from("<HBBII", data, i)
        if magic != 0x50AA:
            break
        if ptype == 0 and sub in (0x00, 0x10) and off == APP_OFFSET:
            return True
    return False


# ---------------------------------------------------------------- catalog and downloads

def fetch_catalog(url=CATALOG_URL):
    req = urllib.request.Request(url, headers={"User-Agent": f"DotGlowFlasher/{VERSION}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def firmware_for(catalog, board):
    """-> dict(name, version, app, appMd5, full, fullMd5) for a board key, or None."""
    if board == "esp8266":
        e = catalog.get("esp8266")
        if not e:
            return None
        return {"name": e.get("name", "Matrix Clock for ESP8266"), "version": e["version"], "full": e["full"],
                "fullMd5": e.get("fullMd5"), "app": None, "appMd5": None}
    e = catalog.get("dotglow", {})
    b = e.get("boards", {}).get(board)
    if not b:
        return None
    return {"name": "DotGlow", "version": e["version"], "full": b["full"], "fullMd5": b.get("fullMd5"),
            "app": b.get("app"), "appMd5": b.get("appMd5")}


def download(url, md5=None, on_progress=lambda done, total: None):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, re.sub(r"[^A-Za-z0-9._-]", "_", url.split("://", 1)[-1]))
    if md5 and os.path.exists(path) and _md5(path) == md5:
        on_progress(1, 1)
        return path                                              # already downloaded
    req = urllib.request.Request(url, headers={"User-Agent": f"DotGlowFlasher/{VERSION}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        with open(path + ".part", "wb") as f:
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                on_progress(done, total)
    os.replace(path + ".part", path)
    if md5 and _md5(path) != md5:
        os.remove(path)
        raise RuntimeError("The downloaded file is damaged (checksum mismatch). Try again.")
    return path


def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- the install itself

def install(port, baud, board, fw, update, erase, on_text, on_status, on_dl_progress, custom=None):
    """Download if needed and flash. Returns True on success. custom = (path, address) overrides the catalog."""
    if custom:
        path, addr = custom
        on_status("Flashing your file...")
        return run_esptool(["--port", port, "--baud", baud, "write-flash", addr, path], on_text) == 0
    if update and fw["app"]:
        on_status("Downloading the app image...")
        path = download(fw["app"], fw["appMd5"], on_dl_progress)
        on_status("Updating (your settings are kept)...")
        if run_esptool(["--port", port, "--baud", baud, "erase-region", hex(OTADATA[0]), hex(OTADATA[1])], on_text) != 0:
            return False
        return run_esptool(["--port", port, "--baud", baud, "write-flash", hex(APP_OFFSET), path], on_text) == 0
    on_status("Downloading the firmware...")
    path = download(fw["full"], fw["fullMd5"], on_dl_progress)
    if erase:
        on_status("Erasing the flash...")
        if run_esptool(["--port", port, "--baud", baud, "erase-flash"], on_text) != 0:
            return False
    on_status("Installing... do not unplug the board")
    args = ["--port", port, "--baud", baud, "write-flash"]
    if board in ("esp32", "esp32s3"):
        args += ["--flash-size", "4MB"]
    return run_esptool(args + ["0x0", path], on_text) == 0


# ---------------------------------------------------------------- command line

def cli(argv):
    ap = argparse.ArgumentParser(prog="dotglow-flasher", description="Install DotGlow firmware on an ESP board.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list", help="list serial ports")
    for name, help_ in (("detect", "show chip, MAC and flash size"), ("flash", "download the latest firmware and install it")):
        p = sub.add_parser(name, help=help_)
        p.add_argument("--port", help="COM5, /dev/ttyUSB0 ... (default: the only ESP-like port)")
        p.add_argument("--baud", type=int, default=460800 if name == "flash" else 115200)
        if name == "flash":
            p.add_argument("--update", action="store_true", help="keep settings (ESP32 / ESP32-S3 running DotGlow)")
            p.add_argument("--erase", action="store_true", help="erase the whole flash first")
            p.add_argument("--file", help="flash this .bin instead of the latest release")
            p.add_argument("--addr", default="0x0", help="address for --file (default 0x0)")
            p.add_argument("--board", choices=["esp32", "esp32s3", "esp8266"], help="skip chip detection")
            p.add_argument("--yes", "-y", action="store_true", help="do not ask")
    a = ap.parse_args(argv)
    if a.cmd is None:
        ap.print_help()
        return 0
    if a.cmd == "list":
        ports = list_ports()
        for dev, desc, likely in ports:
            print(f"{dev:12} {desc}{'   <- looks like an ESP board' if likely else ''}")
        if not ports:
            print("No serial ports found. Plug the board in with a USB data cable.")
        return 0
    port = a.port
    if not port:
        likely = [p for p in list_ports() if p[2]]
        if len(likely) != 1:
            print("Which port? Use --port (see: list).")
            return 2
        port = likely[0][0]
    print(f"Port {port}: detecting the chip...")
    info = detect(port, 115200)
    if not info["ok"]:
        print(info["text"].strip()[-600:])
        print("\nCould not talk to the board. Use a data cable, keep other wires off the board, hold BOOT while retrying.")
        return 1
    print(f"Chip: {info['chip']}   MAC: {info['mac']}   Flash: {info['flash']}")
    if a.cmd == "detect":
        return 0
    board = getattr(a, "board", None) or info["board"]
    if not board and not a.file:
        print("This chip is not supported by DotGlow (ESP32, ESP32-S3 and ESP8266 are).")
        return 1
    custom = (a.file, a.addr) if a.file else None
    fw = None
    if not custom:
        fw = firmware_for(fetch_catalog(), board)
        if not fw:
            print(f"No firmware listed for {board}.")
            return 1
        print(f"Firmware: {fw['name']} {fw['version']}  ({'update, settings kept' if a.update else 'full install'})")
        if a.update and not has_dotglow_layout(port, a.baud):
            print("This board does not run DotGlow yet, so a full install is needed (leave out --update).")
            return 1
    if not a.yes:
        if input("Install now? This replaces the firmware on the board. [y/N] ").strip().lower() != "y":
            return 1
    last = [0]

    def progress(done, total):
        if total and done * 100 // total != last[0]:
            last[0] = done * 100 // total
            print(f"\rDownloading {last[0]:3d}%", end="", flush=True)

    out = sys.stdout                       # the real console: esptool's own output is captured and sent here

    def show(s):
        out.write(s)
        out.flush()

    ok = install(port, a.baud, board, fw, a.update, a.erase, show, lambda s: show(f"\n== {s}\n"), progress, custom)
    print("\nDone. The board restarted." if ok else "\nInstall failed. See the messages above.")
    return 0 if ok else 1


# ---------------------------------------------------------------- window

def gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    BG, PANEL, FG, MUTED, RED, GOOD = "#0c0e13", "#171a22", "#e9ebf1", "#9aa1b0", "#ff3b3b", "#35d07f"
    root = tk.Tk()
    root.title(f"DotGlow Flasher {VERSION}")
    root.geometry("820x700")
    root.minsize(760, 640)
    root.configure(bg=BG)
    try:
        icon = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(__file__)), "icon.png")
        root.iconphoto(True, tk.PhotoImage(file=icon))
    except Exception:                                            # noqa: BLE001
        pass
    st = ttk.Style()
    st.theme_use("clam")
    st.configure(".", background=BG, foreground=FG, fieldbackground=PANEL, font=("Segoe UI", 10))
    st.configure("Panel.TFrame", background=PANEL)
    st.configure("TLabel", background=BG, foreground=FG)
    st.configure("Panel.TLabel", background=PANEL, foreground=FG)
    st.configure("Muted.TLabel", background=PANEL, foreground=MUTED)
    st.configure("H.TLabel", background=PANEL, foreground=RED, font=("Segoe UI", 9, "bold"))
    st.configure("Title.TLabel", background=BG, foreground=FG, font=("Segoe UI", 20, "bold"))
    st.configure("TCheckbutton", background=PANEL, foreground=FG)
    st.map("TCheckbutton", background=[("active", PANEL)])
    st.configure("TCombobox", fieldbackground="#222633", background="#222633", foreground=FG, arrowcolor=FG,
                 selectbackground="#222633", selectforeground=FG)
    st.map("TCombobox", fieldbackground=[("readonly", "#222633")], foreground=[("readonly", FG)],
           selectbackground=[("readonly", "#222633")], selectforeground=[("readonly", FG)])
    root.option_add("*TCombobox*Listbox.background", "#222633")
    root.option_add("*TCombobox*Listbox.foreground", FG)
    root.option_add("*TCombobox*Listbox.selectBackground", RED)
    root.option_add("*TCombobox*Listbox.selectForeground", "white")
    st.configure("TEntry", fieldbackground="#222633", foreground=FG, insertcolor=FG)
    st.configure("TButton", background="#262a36", foreground=FG, padding=7, borderwidth=0)
    st.map("TButton", background=[("active", "#323849")])
    st.configure("Go.TButton", background=RED, foreground="white", font=("Segoe UI", 13, "bold"), padding=12)
    st.map("Go.TButton", background=[("active", "#ff5a5a"), ("disabled", "#5a2a2e")])
    st.configure("Horizontal.TProgressbar", troughcolor=PANEL, background=RED, bordercolor=PANEL, lightcolor=RED, darkcolor=RED)

    ports_var, status_var = tk.StringVar(), tk.StringVar(value="Plug in your board, then press Detect.")
    chip_var, fw_var = tk.StringVar(value="No board detected yet"), tk.StringVar(value="Firmware list not loaded")
    update_var, erase_var = tk.BooleanVar(value=False), tk.BooleanVar(value=False)
    baud_var = tk.StringVar(value="460800")
    file_var, addr_var = tk.StringVar(), tk.StringVar(value="0x0")
    state = {"board": None, "fw": None, "busy": False, "catalog": None, "port_map": {}, "likely": []}
    q = queue.Queue()

    ttk.Label(root, text="DotGlow Flasher", style="Title.TLabel").pack(anchor="w", padx=22, pady=(16, 0))
    ttk.Label(root, text="Install DotGlow on an ESP32, ESP32-S3 or ESP8266 board. No drivers to configure, no code.",
              foreground=MUTED).pack(anchor="w", padx=22, pady=(0, 10))

    def card(title):
        f = ttk.Frame(root, style="Panel.TFrame", padding=14)
        f.pack(fill="x", padx=18, pady=5)
        ttk.Label(f, text=title, style="H.TLabel").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))
        f.columnconfigure(1, weight=1)
        return f

    c1 = card("1  BOARD")
    port_box = ttk.Combobox(c1, textvariable=ports_var, state="readonly", width=46)
    port_box.grid(row=1, column=0, columnspan=2, sticky="we", padx=(0, 8))
    ttk.Button(c1, text="Refresh", command=lambda: refresh_ports()).grid(row=1, column=2, padx=3)
    detect_btn = ttk.Button(c1, text="Detect", command=lambda: start_detect())
    detect_btn.grid(row=1, column=3, padx=3)
    ttk.Label(c1, textvariable=chip_var, style="Muted.TLabel").grid(row=2, column=0, columnspan=4, sticky="w", pady=(8, 0))

    c2 = card("2  FIRMWARE")
    ttk.Label(c2, textvariable=fw_var, style="Panel.TLabel", font=("Segoe UI", 11, "bold")).grid(row=1, column=0, columnspan=4, sticky="w")
    upd_chk = ttk.Checkbutton(c2, text="Keep my WiFi and settings (update only; the board must already run DotGlow)",
                              variable=update_var)
    upd_chk.grid(row=2, column=0, columnspan=4, sticky="w", pady=(8, 0))
    ttk.Checkbutton(c2, text="Erase everything first (fixes a board that behaves strangely)", variable=erase_var).grid(
        row=3, column=0, columnspan=4, sticky="w")

    c3 = card("3  INSTALL")
    go = ttk.Button(c3, text="Install firmware", style="Go.TButton", command=lambda: start_install())
    go.grid(row=1, column=0, columnspan=4, sticky="we")
    bar = ttk.Progressbar(c3, maximum=100)
    bar.grid(row=2, column=0, columnspan=4, sticky="we", pady=(10, 2))
    ttk.Label(c3, textvariable=status_var, style="Muted.TLabel").grid(row=3, column=0, columnspan=4, sticky="w")

    adv_open = tk.BooleanVar(value=False)
    adv = ttk.Frame(root, style="Panel.TFrame", padding=14)

    def toggle_adv():
        if adv_open.get():
            adv.pack_forget()
            adv_open.set(False)
            adv_btn.config(text="Advanced  +")
        else:
            adv.pack(fill="x", padx=18, pady=5, before=log_frame)
            adv_open.set(True)
            adv_btn.config(text="Advanced  -")

    adv_btn = ttk.Button(root, text="Advanced  +", command=toggle_adv)
    adv_btn.pack(anchor="w", padx=18, pady=(4, 0))
    ttk.Label(adv, text="Speed (baud)", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
    ttk.Combobox(adv, textvariable=baud_var, values=["115200", "230400", "460800", "921600"], width=10, state="readonly").grid(
        row=0, column=1, sticky="w", padx=8)
    ttk.Label(adv, text="Slower is safer on long or thin cables.", style="Muted.TLabel").grid(row=0, column=2, columnspan=2, sticky="w")
    ttk.Label(adv, text="Your own .bin", style="Panel.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))
    ttk.Entry(adv, textvariable=file_var, width=44).grid(row=1, column=1, columnspan=2, sticky="we", padx=8, pady=(8, 0))
    ttk.Button(adv, text="Browse", command=lambda: file_var.set(
        filedialog.askopenfilename(filetypes=[("Firmware", "*.bin")]) or file_var.get())).grid(row=1, column=3, pady=(8, 0))
    ttk.Label(adv, text="Address", style="Panel.TLabel").grid(row=2, column=0, sticky="w")
    ttk.Entry(adv, textvariable=addr_var, width=12).grid(row=2, column=1, sticky="w", padx=8)
    ttk.Label(adv, text="Leave the .bin empty to install the latest release.", style="Muted.TLabel").grid(row=2, column=2, columnspan=2, sticky="w")

    log_frame = ttk.Frame(root, style="Panel.TFrame", padding=8)
    log_frame.pack(fill="both", expand=True, padx=18, pady=(8, 14))
    log = tk.Text(log_frame, height=8, bg="#0a0c10", fg="#c6cbd6", relief="flat", font=("Consolas", 9), wrap="word")
    log.pack(fill="both", expand=True)
    log.configure(state="disabled")

    def log_add(s):
        log.configure(state="normal")
        log.insert("end", s)
        log.see("end")
        log.configure(state="disabled")

    def refresh_go():
        ready = not state["busy"] and bool(state["fw"] or file_var.get().strip())
        go.config(state="normal" if ready else "disabled")

    def set_busy(b):
        state["busy"] = b
        detect_btn.config(state="disabled" if b else "normal")
        refresh_go()

    def refresh_ports():
        ports = list_ports()
        state["port_map"] = {f"{d}  -  {desc}": d for d, desc, _ in ports}
        state["likely"] = [f"{d}  -  {desc}" for d, desc, likely in ports if likely]
        names = list(state["port_map"])
        port_box["values"] = names
        if state["likely"]:
            if ports_var.get() not in state["likely"]:
                ports_var.set(state["likely"][0])
            status_var.set("Board found. Press Detect." if len(state["likely"]) == 1 else "Pick your board in the list, then press Detect.")
        else:
            ports_var.set(names[0] if names else "")
            status_var.set("No ESP board found. Plug it in with a USB data cable (some cables only charge), then press Refresh.")
        return names

    def need_port():
        port = state["port_map"].get(ports_var.get())
        if not port:
            messagebox.showinfo("DotGlow Flasher", "Plug the board in and press Refresh.")
        return port

    def load_catalog():
        try:
            state["catalog"] = fetch_catalog()
            q.put(("catalog", None))
        except Exception as e:                                   # noqa: BLE001
            q.put(("status", f"Could not load the firmware list ({e}). Check your internet connection."))

    def start_detect():
        port = need_port()
        if not port or state["busy"]:
            return
        set_busy(True)
        chip_var.set("Detecting...")
        status_var.set("Talking to the board...")

        def work():
            info = detect(port, 115200)
            q.put(("detected", info))
        threading.Thread(target=work, daemon=True).start()

    def start_install():
        if state["busy"]:
            return
        port = need_port()
        if not port:
            return
        custom = None
        if file_var.get().strip():
            custom = (file_var.get().strip(), addr_var.get().strip() or "0x0")
        elif not state["fw"]:
            messagebox.showinfo("DotGlow Flasher", "Press Detect first, so I know which firmware your board needs.")
            return
        if not messagebox.askyesno("Install", "This replaces the firmware on the board.\n\nDo not unplug it until it says Done.\n\nContinue?"):
            return
        set_busy(True)
        bar["value"] = 0
        log_add("\n--- install ---\n")
        buf = {"line": ""}

        def on_text(s):
            for part in re.split(r"([\r\n])", s):
                if part in ("\r", "\n"):
                    line = buf["line"]
                    buf["line"] = ""
                    m = re.search(r"(\d+(?:\.\d+)?)\s*%", line)
                    if "Writing at" in line and m:
                        q.put(("bar", float(m.group(1))))
                    elif line.strip():
                        q.put(("log", line.strip() + "\n"))
                else:
                    buf["line"] += part

        def work():
            try:
                baud = int(baud_var.get())
                update = update_var.get()
                if update and not custom and not has_dotglow_layout(port, baud):
                    q.put(("log", "This board does not run DotGlow yet: doing a full install instead.\n"))
                    update = False
                ok = install(port, baud, state["board"], state["fw"], update, erase_var.get(), on_text,
                             lambda s: q.put(("status", s)), lambda d, t: q.put(("bar", d * 100 / t if t else 0)), custom)
            except Exception as e:                               # noqa: BLE001
                q.put(("log", f"Error: {e}\n"))
                ok = False
            q.put(("done", ok))
        threading.Thread(target=work, daemon=True).start()

    def pump():
        try:
            while True:
                kind, val = q.get_nowait()
                if kind == "log":
                    log_add(val)
                elif kind == "status":
                    status_var.set(val)
                elif kind == "bar":
                    bar["value"] = val
                elif kind == "catalog":
                    if state["board"]:
                        show_fw()
                    else:
                        fw_var.set("Press Detect to see the firmware for your board")
                elif kind == "detected":
                    set_busy(False)
                    if not val["ok"]:
                        chip_var.set("Could not talk to the board")
                        status_var.set("Check the USB data cable, remove other wires from the board, hold BOOT and try again.")
                        log_add(val["text"][-700:] + "\n")
                    else:
                        state["board"] = val["board"]
                        chip_var.set(f"{val['chip']}   MAC {val['mac']}   Flash {val['flash']}")
                        status_var.set("Board found.")
                        show_fw()
                elif kind == "done":
                    set_busy(False)
                    if val:
                        bar["value"] = 100
                        status_var.set("Done. The board restarted. Open the DotGlow app to set it up.")
                        messagebox.showinfo("DotGlow Flasher", "Done! The board restarted.")
                    else:
                        status_var.set("Install failed. Use a data cable, take other wires off the board, try a slower speed.")
        except queue.Empty:
            pass
        root.after(80, pump)

    def show_fw():
        board = state["board"]
        if not board:
            fw_var.set("This chip is not supported by DotGlow (ESP32, ESP32-S3, ESP8266).")
            state["fw"] = None
            refresh_go()
            return
        if not state["catalog"]:
            fw_var.set("Loading the firmware list...")
            return
        fw = firmware_for(state["catalog"], board)
        state["fw"] = fw
        if not fw:
            fw_var.set(f"No firmware listed for {board}")
            return
        fw_var.set(f"{fw['name']}  {fw['version']}   (latest, for {board.upper().replace('ESP32S3', 'ESP32-S3')})")
        refresh_go()
        upd_chk.state(["!disabled"] if fw["app"] else ["disabled"])
        if not fw["app"]:
            update_var.set(False)

    shot = os.environ.get("DOTGLOW_FLASHER_SHOT")      # self-test: save a picture of this window only, then quit
    if shot:
        def take():
            from PIL import ImageGrab
            root.update()
            x, y, w, h = root.winfo_rootx(), root.winfo_rooty(), root.winfo_width(), root.winfo_height()
            ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(shot)
            root.destroy()
        root.attributes("-topmost", True)
        root.after(4500, take)

    file_var.trace_add("write", lambda *_: refresh_go())
    refresh_ports()
    refresh_go()
    threading.Thread(target=load_catalog, daemon=True).start()
    pump()
    if len(state["likely"]) == 1:                                # exactly one board plugged in: detect it right away
        root.after(400, start_detect)
    root.mainloop()


def main():
    if len(sys.argv) > 1:
        sys.exit(cli(sys.argv[1:]))
    if "cli" in os.path.basename(sys.argv[0]).lower():           # console build: show the help, not the window
        sys.exit(cli(["--help"]))
    gui()


if __name__ == "__main__":
    main()
