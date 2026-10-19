# Rebuild everything: netlist -> placed board -> routed board -> fab files, then the layout-only package.
# Run from the repo root in PowerShell.  KiCad 10 must be installed (per-user or Program Files).
$ErrorActionPreference = "Stop"
$kb = "$env:LOCALAPPDATA\Programs\KiCad\10.0\bin"; if (-not (Test-Path $kb)) { $kb = "C:\Program Files\KiCad\10.0\bin" }
$kp = "$kb\python.exe"; $cli = "$kb\kicad-cli.exe"
$env:TG_NO_ZONES = "1"; $env:ROUTE_GND = "0"
& $kp hardware\pcb\generate_kicad.py
& $kp hardware\pcb\route_pcb.py | Select-String "failed|saved"
python hardware\pcb\export_fab.py | Select-Object -Last 1
# layout-only package
$L = "hardware\pcb\layout"; $env:DG_OUT = "$PWD\$L\kicad"; $env:TG_NO_ZONES = ""
& $kp hardware\pcb\generate_kicad.py
$pcb = "$L\kicad\dotglow-v1.kicad_pcb"
& $cli pcb export pdf --layers "Edge.Cuts,F.Courtyard,F.Silkscreen,F.Fab,Dwgs.User" --black-and-white -o "$L\dotglow-v1-layout.pdf" $pcb
& $cli pcb export dxf --mode-single --use-drill-origin --output-units mm --layers "Edge.Cuts,F.Courtyard,F.Silkscreen,Dwgs.User" -o "$L\dotglow-v1-full-layout.dxf" $pcb
python hardware\pcb\make_layout_files.py
