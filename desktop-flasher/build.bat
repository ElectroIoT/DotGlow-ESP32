@echo off
rem Builds dist\DotGlowFlasher.exe (window) and dist\dotglow-flasher-cli.exe (command line). Needs Python 3.10+.
cd /d "%~dp0"
python -m pip install -r requirements.txt || exit /b 1
python -m PyInstaller --noconfirm --clean --onefile --windowed --name DotGlowFlasher --icon icon.ico ^
  --add-data "icon.png;." --collect-all esptool --hidden-import serial.tools.list_ports_windows dotglow_flasher.py || exit /b 1
python -m PyInstaller --noconfirm --onefile --console --name dotglow-flasher-cli --icon icon.ico ^
  --collect-all esptool --hidden-import serial.tools.list_ports_windows dotglow_flasher.py || exit /b 1
echo Done: dist\DotGlowFlasher.exe and dist\dotglow-flasher-cli.exe
