"""Publish the release files to the web flasher (mtpcode.com/flash/).

    python tools/make_web_flasher.py [path-to-mtpcode-repo]        default: D:/My Project/mtpcode

Copies release/<version>/dotglow-esp32-full.bin, dotglow-esp32s3-full.bin and the ESP8266 firmware into
<site>/public/flash/fw/ and writes the two ESP Web Tools manifests next to them. Then commit + push the site repo
(GitHub Actions deploys it). Run it after tools/release.py, with the same version.
"""
import json
import os
import re
import shutil
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = sys.argv[1] if len(sys.argv) > 1 else 'D:/My Project/mtpcode'
CATALOG = 'https://manoranjan.dev/dotglow/firmware.json'


def main():
    # same line release.py uses: the one marked "bump" (an earlier #define is the safe-mode test build)
    version = re.search(r'#define FW_VERSION\s+"([^"]+)"\s*//\s*bump',
                        open(os.path.join(ROOT, 'src', 'config.h')).read()).group(1)
    rel = os.path.join(ROOT, 'release', version)
    out = os.path.join(SITE, 'public', 'flash')
    fw = os.path.join(out, 'fw')
    os.makedirs(fw, exist_ok=True)
    for name in ('dotglow-esp32-full.bin', 'dotglow-esp32s3-full.bin'):
        shutil.copyfile(os.path.join(rel, name), os.path.join(fw, name))
    shutil.copyfile(os.path.join(rel, 'esp8266', 'firmware.bin'), os.path.join(fw, 'esp8266-matrix-clock.bin'))
    req = urllib.request.Request(CATALOG, headers={'User-Agent': 'DotGlowReleaseTool/1.0'})   # the host rejects the default Python agent
    with urllib.request.urlopen(req, timeout=20) as r:
        esp8266_version = json.load(r)['esp8266']['version']

    def manifest(name, ver, builds):
        return {'name': name, 'version': ver, 'new_install_prompt_erase': True, 'builds': builds}

    dotglow = manifest('DotGlow', version, [
        {'chipFamily': 'ESP32', 'parts': [{'path': 'fw/dotglow-esp32-full.bin', 'offset': 0}]},
        {'chipFamily': 'ESP32-S3', 'parts': [{'path': 'fw/dotglow-esp32s3-full.bin', 'offset': 0}]},
    ])
    esp8266 = manifest('Matrix Clock for ESP8266', esp8266_version, [
        {'chipFamily': 'ESP8266', 'parts': [{'path': 'fw/esp8266-matrix-clock.bin', 'offset': 0}]},
    ])
    for fname, data in (('manifest-dotglow.json', dotglow), ('manifest-esp8266.json', esp8266)):
        with open(os.path.join(out, fname), 'w', encoding='utf-8', newline='\n') as f:
            json.dump(data, f, indent=2)
            f.write('\n')
    print(f'web flasher files written to {out}: DotGlow {version}, ESP8266 {esp8266_version}')


if __name__ == '__main__':
    main()
