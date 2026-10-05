#!/bin/bash
# Exports every board preset: screw + snap backs, shells with and without the stopwatch button.
cd "$(dirname "$0")"
O="${OPENSCAD:-/c/Program Files/OpenSCAD/openscad.com}"
rm -rf stl && mkdir -p stl
"$O" -o stl/dotglow-testfit.stl -D 'part="testfit"' dotglow_case.scad 2>&1 | grep -E "ERROR" 
for b in esp32s3:esp32-s3 esp32_30pin:esp32-devkit-30pin esp32_38pin:esp32-devkit-38pin nodemcu_v2:esp8266-nodemcu-v2 nodemcu_v3:esp8266-nodemcu-v3 d1_mini:esp8266-d1-mini; do
  key=${b%%:*}; dir=stl/${b##*:}; mkdir -p "$dir"
  for fix in screw snap; do
    sfx=""; [ $fix = snap ] && sfx="-snap"
    "$O" -o "$dir/shell$sfx-button.stl"    -D 'part="shell"' -D "board=\"$key\"" -D "back_fix=\"$fix\"" dotglow_case.scad 2>&1 | grep -E "ERROR"
    "$O" -o "$dir/shell$sfx-no-button.stl" -D 'part="shell"' -D "board=\"$key\"" -D "back_fix=\"$fix\"" -D 'button="none"' dotglow_case.scad 2>&1 | grep -E "ERROR"
    "$O" -o "$dir/back$sfx.stl"            -D 'part="back"'  -D "board=\"$key\"" -D "back_fix=\"$fix\"" dotglow_case.scad 2>&1 | grep -E "ERROR"
  done
  echo "done $key"
done
mkdir -p stl/extras
"$O" -o stl/extras/esp32-s3-shell-lean30-button.stl -D 'part="shell"' -D 'lean=30' dotglow_case.scad 2>&1 | grep -E "ERROR"
"$O" -o stl/extras/esp32-s3-back-panel-jack.stl -D 'part="back"' -D 'dc_jack="panel"' dotglow_case.scad 2>&1 | grep -E "ERROR"
"$O" -o stl/extras/esp32-s3-back-tape.stl -D 'part="back"' -D 'board_mount="tape"' dotglow_case.scad 2>&1 | grep -E "ERROR"
echo ALL DONE
