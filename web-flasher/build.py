"""Build the web flasher site (GitHub Pages) from the firmware catalog.

    python web-flasher/build.py [output-folder]        default: _site

The page (index.html, icon.png) comes from this folder. The firmware is not kept in git: it is downloaded
from the same catalog the phone app and the PC flasher use, checked against its size and MD5, and put next
to the ESP Web Tools manifests (the browser needs it on the same site as the page).
"""
import hashlib
import json
import shutil
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATALOG = 'https://manoranjan.dev/dotglow/firmware.json'
CHIPS = {'esp32': 'ESP32', 'esp32s3': 'ESP32-S3'}


def get(url):
    if not url.startswith('https://'):
        raise SystemExit(f'refusing a link that is not https: {url}')
    # the firmware host rejects the default Python agent
    req = urllib.request.Request(url, headers={'User-Agent': 'DotGlowReleaseTool/1.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def firmware(entry, target):
    data = get(entry['full'])
    if len(data) != entry['fullSize'] or hashlib.md5(data).hexdigest() != entry['fullMd5'].lower():
        raise SystemExit(f"{entry['full']}: size or MD5 differs from the catalog")
    target.write_bytes(data)
    print(f'{target.name}: {len(data)} bytes, checksum ok')


def manifest(path, name, version, builds):
    data = {'name': name, 'version': version, 'new_install_prompt_erase': True, 'builds': builds}
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else '_site')
    fw = out / 'fw'
    fw.mkdir(parents=True, exist_ok=True)
    for name in ('index.html', 'icon.png'):
        shutil.copyfile(HERE / name, out / name)

    catalog = json.loads(get(CATALOG))
    dotglow, esp8266 = catalog['dotglow'], catalog['esp8266']
    builds = []
    for key, family in CHIPS.items():
        file = f'dotglow-{key}-full.bin'
        firmware(dotglow['boards'][key], fw / file)
        builds.append({'chipFamily': family, 'parts': [{'path': f'fw/{file}', 'offset': 0}]})
    manifest(out / 'manifest-dotglow.json', 'DotGlow', dotglow['version'], builds)

    firmware(esp8266, fw / 'esp8266-matrix-clock.bin')
    manifest(out / 'manifest-esp8266.json', esp8266['name'], esp8266['version'],
             [{'chipFamily': 'ESP8266', 'parts': [{'path': 'fw/esp8266-matrix-clock.bin', 'offset': 0}]}])
    print(f"site written to {out}: DotGlow {dotglow['version']}, ESP8266 {esp8266['version']}")


if __name__ == '__main__':
    main()
