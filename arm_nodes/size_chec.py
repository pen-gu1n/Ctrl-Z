# stl_size.py
import re
import struct
import sys

path = sys.argv[1]
data = open(path, 'rb').read()

xs, ys, zs = [], [], []

def is_binary(d):
    if len(d) < 84:
        return False
    n = struct.unpack('<I', d[80:84])[0]
    return len(d) == 84 + 50 * n

if is_binary(data):
    n = struct.unpack('<I', data[80:84])[0]
    for i in range(n):
        off = 84 + 50 * i
        v = struct.unpack('<12f', data[off:off + 48])
        for j in (3, 6, 9):   # 3頂点ぶん
            xs.append(v[j]); ys.append(v[j + 1]); zs.append(v[j + 2])
    print(f"binary STL, triangles={n}")
else:
    text = data.decode('utf-8', errors='ignore')
    for m in re.finditer(r'vertex\s+(\S+)\s+(\S+)\s+(\S+)', text):
        x, y, z = map(float, m.groups())
        xs.append(x); ys.append(y); zs.append(z)
    print(f"ascii STL, vertices={len(xs)}")

if not xs:
    sys.exit("頂点が読み取れませんでした")

mn = (min(xs), min(ys), min(zs))
mx = (max(xs), max(ys), max(zs))
print("min :", mn)
print("max :", mx)
print("size:", tuple(b - a for a, b in zip(mn, mx)))