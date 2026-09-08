"""Rasterise Natural Earth land and lakes onto the 0.1-degree grid the DEM uses."""
import json, numpy as np
from PIL import Image, ImageDraw
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _os.path.join(_HERE, "..", "cli"))
# Where the downloaded source datasets live. Override with WAYFARE_SOURCES.
SRC = _os.environ.get("WAYFARE_SOURCES", _os.path.join(_HERE, "sources"))
Image.MAX_IMAGE_PIXELS = None

RES = 0.1
W, H = int(360/RES), int(180/RES)

def rings(geom):
    t, c = geom["type"], geom["coordinates"]
    if t == "Polygon":       return [c]
    if t == "MultiPolygon":  return c
    return []

def px(ring):
    return [((lon+180)/RES, (90-lat)/RES) for lon, lat in ring]

img = Image.new("1", (W, H), 0)
d = ImageDraw.Draw(img)
land = json.load(open(f"{SRC}/ne_10m_land.json"))
n = 0
for f in land["features"]:
    for poly in rings(f["geometry"]):
        d.polygon(px(poly[0]), fill=1)
        for hole in poly[1:]:
            d.polygon(px(hole), fill=0)
        n += 1
print("land polygons:", n)

lakes = json.load(open(f"{SRC}/ne_10m_lakes.json"))
nl = 0
for f in lakes["features"]:
    for poly in rings(f["geometry"]):
        d.polygon(px(poly[0]), fill=0)
        nl += 1
print("lakes:", nl)

m = np.array(img, dtype=np.uint8)
np.save("landmask_0p1.npy", m)
print(f"{W}x{H}, land {m.sum():,} cells = {100*m.mean():.1f}%")
