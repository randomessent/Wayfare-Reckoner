"""The routing mask: real coastline at 0.1 degrees, with the narrow waters a
raster closes forced open, and the modern canals forced shut."""
import json, numpy as np
from PIL import Image, ImageDraw
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _os.path.join(_HERE, "..", "cli"))
# Where the downloaded source datasets live. Override with WAYFARE_SOURCES.
SRC = _os.environ.get("WAYFARE_SOURCES", _os.path.join(_HERE, "sources"))

RES = 0.1
W, H = int(360/RES), int(180/RES)

# narrow waters a 11 km grid welds shut
STRAITS = [
 ("Gibraltar", (-5.75,35.85), (-5.20,36.10)),
 ("Bosphorus", (29.20,41.35), (28.95,40.95)),
 ("Dardanelles", (26.70,40.45), (26.15,40.00)),
 ("Messina", (15.55,38.35), (15.75,37.95)),
 ("Oresund", (12.55,56.10), (12.95,55.30)),
 ("Great Belt", (10.75,56.00), (11.10,55.15)),
 ("Little Belt", (9.65,55.60), (9.95,55.00)),
 ("Kerch", (36.35,45.45), (36.75,45.15)),
 ("Bab el Mandeb", (43.20,12.80), (43.60,12.45)),
 ("Hormuz", (56.15,26.75), (56.65,26.35)),
 ("Malacca", (100.10,3.20), (101.30,2.10)),
 ("Sunda", (105.40,-5.75), (105.95,-6.35)),
 ("Bass", (145.60,-38.90), (146.60,-40.50)),
 ("Cook", (174.55,-41.05), (173.95,-41.55)),
 ("Tsugaru", (140.30,41.60), (140.90,41.30)),
 ("Korea", (129.20,34.30), (129.70,34.95)),
 ("Bering", (-169.30,66.10), (-170.30,65.25)),
 ("Dover", (1.35,51.20), (1.85,50.90)),
 ("Bonifacio", (9.10,41.45), (9.30,41.28)),
 ("Otranto", (18.45,40.20), (19.35,40.35)),
]
# isthmuses a modern canal has cut, which in this world was never dug
BRIDGES = [
 ("Suez", (32.30,31.20), (32.60,29.90)),
 ("Corinth", (22.90,37.98), (23.05,37.90)),
]

img = Image.new("1", (W, H), 0)
d = ImageDraw.Draw(img)
def rings(g):
    t, c = g["type"], g["coordinates"]
    return [c] if t == "Polygon" else c if t == "MultiPolygon" else []
def px(r): return [((lo+180)/RES, (90-la)/RES) for lo, la in r]

for f in json.load(open(f"{SRC}/ne_10m_land.json"))["features"]:
    for poly in rings(f["geometry"]):
        d.polygon(px(poly[0]), fill=1)
        for hole in poly[1:]:
            d.polygon(px(hole), fill=0)
for f in json.load(open(f"{SRC}/ne_10m_lakes.json"))["features"]:
    for poly in rings(f["geometry"]):
        d.polygon(px(poly[0]), fill=0)

for _n, a, b in BRIDGES:
    d.line(px([a, b]), fill=1, width=3)
for _n, a, b in STRAITS:
    (x0, y0), (x1, y1) = px([a, b])
    dx, dy = x1-x0, y1-y0
    k = max(abs(dx), abs(dy), 1)
    ex, ey = dx/k*2.0, dy/k*2.0
    d.line([(x0-ex, y0-ey), (x1+ex, y1+ey)], fill=0, width=2)

m = np.array(img, dtype=np.uint8)
np.save("landmask_0p1.npy", m)
print(f"{W}x{H}, land {100*m.mean():.1f}%")

# connectivity: everything that matters must be reachable on foot
from collections import deque
def cell(la, lo): return int((lo+180)/RES), int((90-la)/RES)
def flood(seed):
    si, sj = cell(*seed)
    seen = np.zeros_like(m, dtype=bool)
    q = deque([(si, sj)]); seen[sj, si] = True
    while q:
        i, j = q.popleft()
        for di in (-1,0,1):
            for dj in (-1,0,1):
                ni, nj = (i+di) % W, j+dj
                if 0 <= nj < H and m[nj, ni] and not seen[nj, ni]:
                    seen[nj, ni] = True; q.append((ni, nj))
    return seen
reach = flood((40.4, -3.7))     # from Madrid
for name, (la, lo) in {"Berlin":(52.5,13.4),"Beijing":(39.9,116.4),"Cape Town":(-33.9,18.4),
                       "Delhi":(28.6,77.2),"Jerusalem":(31.8,35.2),"Singapore":(1.35,103.8),
                       "Vladivostok":(43.1,131.9),"Timbuktu":(16.8,-3.0)}.items():
    i, j = cell(la, lo)
    print(("reachable  " if reach[j, i] else "CUT OFF    "), name)
for name, (la, lo) in {"London":(51.5,-0.13),"Dublin":(53.3,-6.3),"Tokyo":(35.7,139.7),
                       "New York":(40.7,-74.0),"Sydney":(-33.9,151.2)}.items():
    i, j = cell(la, lo)
    print(("(over water, as it should be)" if not reach[j, i] else "WRONGLY WALKABLE"), name)
