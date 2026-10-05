"""Convert ASCII STL files (OpenSCAD 2021) to binary STL, about 5x smaller. Usage: python stl_to_binary.py <dir>"""
import os, re, struct, sys

def convert(path):
    with open(path, 'rb') as f:
        head = f.read(5)
    if head != b'solid':
        return False
    text = open(path, encoding='ascii', errors='ignore').read()
    tris = re.findall(r'facet normal\s+(\S+)\s+(\S+)\s+(\S+).*?vertex\s+(\S+)\s+(\S+)\s+(\S+).*?vertex\s+(\S+)\s+(\S+)\s+(\S+).*?vertex\s+(\S+)\s+(\S+)\s+(\S+)', text, re.S)
    with open(path, 'wb') as f:
        f.write(b'DotGlow case (binary STL)'.ljust(80, b' '))
        f.write(struct.pack('<I', len(tris)))
        for t in tris:
            f.write(struct.pack('<12fH', *map(float, t), 0))
    return True

for root, _, files in os.walk(sys.argv[1] if len(sys.argv) > 1 else 'stl'):
    for name in files:
        if name.lower().endswith('.stl') and convert(os.path.join(root, name)):
            print('binary:', os.path.join(root, name))
