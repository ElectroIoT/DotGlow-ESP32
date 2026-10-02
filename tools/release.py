"""Build the release files into release/<version>/.

    python tools/release.py

For each chip (esp32, esp32s3):
  firmware-<chip>.bin         app only: GitHub / Bluetooth updates of a running clock
  dotglow-<chip>-full.bin     bootloader + partitions + app, flashed at 0x0 on a new board
                              (the app's USB flasher, or: esptool.py write_flash 0x0 <file>)
plus version.txt and firmware.json, the catalog the DotGlow app reads.

firmware.json lists the files under BASE_URL; upload release/<version>/ there and
firmware.json one level up (tools/deploy is not included: copy them however you like).
"""
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIO_HOME = os.path.join(os.path.expanduser('~'), '.platformio')
BASE_URL = 'https://manoranjan.dev/dotglow/fw'

# chip key -> (PlatformIO env, bootloader offset)
CHIPS = {'esp32': ('esp32dev', 0x1000), 'esp32s3': ('esp32s3', 0x0)}

# The ESP8266 version of the clock (separate public repo); the app can flash it too.
ESP8266 = {
    'name': 'Matrix Clock for ESP8266',
    'repo': 'ElectroIoT/ESP8266-Matrix-Clock',
}


def md5(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


def main():
    version = re.search(r'#define FW_VERSION\s+"([^"]+)"\s*//\s*bump',
                        open(os.path.join(ROOT, 'src', 'config.h')).read()).group(1)
    out = os.path.join(ROOT, 'release', version)
    os.makedirs(out, exist_ok=True)
    envs = [env for env, _ in CHIPS.values()]
    subprocess.check_call([sys.executable, '-m', 'platformio', 'run'] + sum((['-e', e] for e in envs), []), cwd=ROOT)

    boot_app0 = os.path.join(PIO_HOME, 'packages', 'framework-arduinoespressif32', 'tools', 'partitions', 'boot_app0.bin')
    catalog = {'version': version, 'boards': {}}
    for chip, (env, boot_at) in CHIPS.items():
        build = os.path.join(ROOT, '.pio', 'build', env)
        app = os.path.join(out, f'firmware-{chip}.bin')
        full = os.path.join(out, f'dotglow-{chip}-full.bin')
        with open(os.path.join(build, 'firmware.bin'), 'rb') as f, open(app, 'wb') as g:
            g.write(f.read())
        subprocess.check_call([
            sys.executable, '-m', 'esptool', '--chip', chip, 'merge-bin', '-o', full,
            '--flash-mode', 'dio', '--flash-freq', '80m' if chip == 'esp32s3' else '40m', '--flash-size', '4MB',
            hex(boot_at), os.path.join(build, 'bootloader.bin'),
            '0x8000', os.path.join(build, 'partitions.bin'),
            '0xe000', boot_app0,
            '0x10000', app,
        ])
        catalog['boards'][chip] = {
            'app': f'{BASE_URL}/{version}/firmware-{chip}.bin', 'appSize': os.path.getsize(app), 'appMd5': md5(app),
            'full': f'{BASE_URL}/{version}/dotglow-{chip}-full.bin', 'fullSize': os.path.getsize(full), 'fullMd5': md5(full),
        }
    open(os.path.join(out, 'version.txt'), 'w').write(version + '\n')

    # ESP8266 clock: latest release of its public repo
    tag = subprocess.check_output(['gh', 'release', 'view', '-R', ESP8266['repo'], '--json', 'tagName', '-q', '.tagName'],
                                  text=True).strip()
    tmp = os.path.join(out, 'esp8266')
    os.makedirs(tmp, exist_ok=True)
    subprocess.check_call(['gh', 'release', 'download', tag, '-R', ESP8266['repo'], '-p', 'firmware.bin', '-D', tmp, '--clobber'])
    bin8266 = os.path.join(tmp, 'firmware.bin')
    esp8266 = {
        'name': ESP8266['name'], 'version': tag.lstrip('v'),
        'full': f'https://github.com/{ESP8266["repo"]}/releases/download/{tag}/firmware.bin',
        'fullSize': os.path.getsize(bin8266), 'fullMd5': md5(bin8266),
    }

    json.dump({'dotglow': catalog, 'esp8266': esp8266}, open(os.path.join(ROOT, 'release', 'firmware.json'), 'w'), indent=2)
    print(f'\nrelease/{version}/ and release/firmware.json are ready')


if __name__ == '__main__':
    main()
