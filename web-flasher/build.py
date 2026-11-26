"""Build the web flasher site (GitHub Pages).

    python web-flasher/build.py [output-folder]        default: _site

The page (index.html, icon.png) comes from this folder. The firmware is not kept in git:
  DotGlow (ESP32, ESP32-S3)  the full images of this repository's latest GitHub release
  ESP8266 Matrix Clock       the entry in the firmware catalog the phone app uses
Every file is checked (size and checksum) and put next to the ESP Web Tools manifests: the browser
needs it on the same site as the page.
"""
import hashlib
import json
import os
import shutil
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RELEASE = 'https://api.github.com/repos/ElectroIoT/DotGlow-ESP32/releases/latest'
CATALOG = 'https://manoranjan.dev/dotglow/firmware.json'
CHIPS = {'esp32': 'ESP32', 'esp32s3': 'ESP32-S3'}


def get(url, token=None):
    if not url.startswith('https://'):
        raise SystemExit(f'refusing a link that is not https: {url}')
    # the firmware catalog's host rejects the default Python agent
    headers = {'User-Agent': 'DotGlowReleaseTool/1.0'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
        return r.read()


def save(url, target, size, algorithm, checksum):
    data = get(url)
    if len(data) != size or hashlib.new(algorithm, data).hexdigest() != checksum.lower():
        raise SystemExit(f'{url}: size or {algorithm} differs from what was published')
    target.write_bytes(data)
    print(f'{target.name}: {len(data)} bytes, {algorithm} ok')


def manifest(path, name, version, builds):
    data = {'name': name, 'version': version, 'new_install_prompt_erase': True, 'builds': builds}
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else '_site')
    fw = out / 'fw'
    fw.mkdir(parents=True, exist_ok=True)
    for name in ('index.html', 'icon.png'):
        shutil.copyfile(HERE / name, out / name)

    release = json.loads(get(RELEASE, os.environ.get('GITHUB_TOKEN')))
    assets = {a['name']: a for a in release['assets']}
    version = release['tag_name'].lstrip('v')
    builds = []
    for key, family in CHIPS.items():
        file = f'dotglow-{key}-full.bin'
        asset = assets[file]
        algorithm, checksum = asset['digest'].split(':', 1)
        save(asset['browser_download_url'], fw / file, asset['size'], algorithm, checksum)
        builds.append({'chipFamily': family, 'parts': [{'path': f'fw/{file}', 'offset': 0}]})
    manifest(out / 'manifest-dotglow.json', 'DotGlow', version, builds)

    esp8266 = json.loads(get(CATALOG))['esp8266']
    save(esp8266['full'], fw / 'esp8266-matrix-clock.bin', esp8266['fullSize'], 'md5', esp8266['fullMd5'])
    manifest(out / 'manifest-esp8266.json', esp8266['name'], esp8266['version'],
             [{'chipFamily': 'ESP8266', 'parts': [{'path': 'fw/esp8266-matrix-clock.bin', 'offset': 0}]}])
    print(f"site written to {out}: DotGlow {version}, ESP8266 {esp8266['version']}")


if __name__ == '__main__':
    main()
