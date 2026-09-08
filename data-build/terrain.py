"""Build the terrain and region-name grids at 0.1 degrees.

Ruggedness comes from ETOPO (mean elevation and local relief per cell), which
is the part boxes and hand-drawn polygons got worst. Biome comes from the
hand-authored regions plus Natural Earth's deserts, because nothing in the
data we have distinguishes forest from grass. Names come from Natural Earth's
1,034 named physical regions.
"""
import json, sys, numpy as np
from PIL import Image, ImageDraw
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _os.path.join(_HERE, "..", "cli"))
# Where the downloaded source datasets live. Override with WAYFARE_SOURCES.
SRC = _os.environ.get("WAYFARE_SOURCES", _os.path.join(_HERE, "sources"))
Image.MAX_IMAGE_PIXELS = None

RES = 0.1
W, H = int(360/RES), int(180/RES)

TERRAINS = ["plain","farmland","river_plain","river_valley","steppe_plain","steppe_plateau",
            "coastal","coastal_karst","hills","upland","forest_plain","forest_hills",
            "forest_upland","marsh_plain","mountain","high_mountain","savanna","desert",
            "sand_sea","rainforest","taiga","tundra","high_plateau","open_water"]
TI = {t: i for i, t in enumerate(TERRAINS)}

land = np.load("landmask_0p1.npy")
elev = np.load(f"{SRC}/dem_mean_0p1.npy").astype(np.int32)
relief = np.load(f"{SRC}/dem_relief_0p1.npy").astype(np.int32)

def rasterise(polys, fill_values):
    """Paint (ring, value) pairs onto a uint8 grid; later entries win."""
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    for ring, v in zip(polys, fill_values):
        d.polygon([((lo+180)/RES, (90-la)/RES) for lo, la in ring], fill=int(v))
    return np.array(img, dtype=np.uint8)

# ── biome layer ───────────────────────────────────────────────────────────
BIOME = ["temperate","tropical","desert","sand_sea","savanna","rainforest","taiga","tundra","marsh","steppe"]
BI = {b: i for i, b in enumerate(BIOME)}
TERRAIN_TO_BIOME = {
    "desert":"desert","sand_sea":"sand_sea","savanna":"savanna","rainforest":"rainforest",
    "taiga":"taiga","tundra":"tundra","marsh_plain":"marsh",
    "steppe_plain":"steppe","steppe_plateau":"steppe","farmland":"temperate",
    "forest_plain":"temperate","forest_hills":"temperate","forest_upland":"temperate",
}
lat_row = 90 - (np.arange(H) + 0.5)*RES
biome = np.full((H, W), BI["temperate"], dtype=np.uint8)
biome[np.abs(lat_row) < 23.5] = BI["tropical"]
biome[(np.abs(lat_row) >= 55) & (np.abs(lat_row) < 68)] = BI["taiga"]
biome[np.abs(lat_row) >= 68] = BI["tundra"]

from regions import REGIONS
rings, vals = [], []
for label, terr, ring in REGIONS:
    b = TERRAIN_TO_BIOME.get(terr)
    if b:
        rings.append(ring); vals.append(BI[b] + 1)
hand = rasterise(rings, vals)
biome = np.where(hand > 0, hand - 1, biome).astype(np.uint8)

ne = json.load(open(f"{SRC}/ne_10m_geography_regions_polys.json"))
def geom_rings(g):
    t, c = g["type"], g["coordinates"]
    return [c[0]] if t == "Polygon" else [p[0] for p in c] if t == "MultiPolygon" else []

drings, dvals = [], []
for f in ne["features"]:
    p = f["properties"]
    if p.get("featurecla") != "Desert":
        continue
    nm = (p.get("name") or "").lower()
    v = BI["sand_sea"] if any(k in nm for k in ("erg", "sand", "nefud", "rub al")) else BI["desert"]
    for r in geom_rings(f["geometry"]):
        drings.append(r); dvals.append(v + 1)
des = rasterise(drings, dvals)
biome = np.where(des > 0, des - 1, biome).astype(np.uint8)
print("biome painted")

# ── ruggedness from the elevation model ───────────────────────────────────
terr = np.full((H, W), TI["open_water"], dtype=np.uint8)
FLAT, HILL, UP, MTN, HIGH = 0, 1, 2, 3, 4
rug = np.zeros((H, W), dtype=np.uint8)
rug[relief >= 150] = HILL
rug[relief >= 350] = UP
rug[relief >= 700] = MTN
rug[((relief >= 1150) & (elev >= 1700)) | (elev >= 3000)] = HIGH

flat_by_biome = {
    BI["temperate"]: "farmland", BI["tropical"]: "forest_plain", BI["desert"]: "desert",
    BI["sand_sea"]: "sand_sea", BI["savanna"]: "savanna", BI["rainforest"]: "rainforest",
    BI["taiga"]: "taiga", BI["tundra"]: "tundra", BI["marsh"]: "marsh_plain",
    BI["steppe"]: "steppe_plain",
}
hill_by_biome = {
    BI["temperate"]: "forest_hills", BI["tropical"]: "forest_hills", BI["desert"]: "desert",
    BI["sand_sea"]: "desert", BI["savanna"]: "hills", BI["rainforest"]: "rainforest",
    BI["taiga"]: "forest_hills", BI["tundra"]: "tundra", BI["marsh"]: "hills",
    BI["steppe"]: "hills",
}
up_by_biome = {
    BI["temperate"]: "forest_upland", BI["tropical"]: "forest_upland", BI["desert"]: "steppe_plateau",
    BI["sand_sea"]: "steppe_plateau", BI["savanna"]: "upland", BI["rainforest"]: "forest_upland",
    BI["taiga"]: "forest_upland", BI["tundra"]: "tundra", BI["marsh"]: "upland",
    BI["steppe"]: "steppe_plateau",
}
for b, name in flat_by_biome.items():
    terr[(rug == FLAT) & (biome == b)] = TI[name]
for b, name in hill_by_biome.items():
    terr[(rug == HILL) & (biome == b)] = TI[name]
for b, name in up_by_biome.items():
    terr[(rug == UP) & (biome == b)] = TI[name]
terr[rug == MTN] = TI["mountain"]
terr[rug == HIGH] = TI["high_mountain"]
# a high, flat place is a plateau, not a plain
terr[(elev >= 2600) & (relief < 900)] = TI["high_plateau"]
terr[(elev >= 1100) & (elev < 2600) & (relief < 250) &
     (np.isin(biome, [BI["temperate"], BI["savanna"], BI["steppe"]]))] = TI["steppe_plateau"]
# the ice sheets are not plateaux anyone crosses like plateaux
lat2d = np.repeat(lat_row[:, None], W, axis=1)
terr[(lat2d < -60)] = TI["tundra"]
terr[(lat2d > 60) & (elev > 1500) & (relief < 700)] = TI["tundra"]

# ── Natural Earth's own words for the special cases ───────────────────────
SPECIAL = {"Wetlands": "marsh_plain", "Delta": "marsh_plain", "Tundra": "tundra",
           "Valley": "river_valley", "Gorge": "mountain"}
srings, svals = [], []
for f in ne["features"]:
    cla = f["properties"].get("featurecla")
    if cla in SPECIAL:
        for r in geom_rings(f["geometry"]):
            srings.append(r); svals.append(TI[SPECIAL[cla]] + 1)
sp = rasterise(srings, svals)
terr = np.where(sp > 0, sp - 1, terr).astype(np.uint8)

terr[land == 0] = TI["open_water"]

# ── names ─────────────────────────────────────────────────────────────────
# Specificity decides who wins. A cell inside both "Península Ibérica" and the
# "Pyrenees" is in the Pyrenees; a traveller says the smaller name. So the vague
# classes go down first, the old provincial names over them, the hand-drawn
# regions over those, and Natural Earth's precise features last of all.
NAME_CLASSES = {"Geoarea", "Peninsula", "Isthmus", "Pen/cape", "Coast", "Lowland",
                "Tundra", "Depression", "Island", "Island group", "Range/mtn",
                "Desert", "Plateau", "Plain", "Basin", "Valley", "Delta",
                "Wetlands", "Foothills", "Gorge"}

names = ["Open Country"]
def name_id(nm):
    if nm not in names:
        names.append(nm)
    return names.index(nm)


def ring_area(ring):
    """Shoelace in square degrees, weighted for the shrinking of longitude.

    This is the whole of the precedence rule: a cell inside both the Península
    Ibérica and the Ebro Valley is in the Ebro Valley, because a traveller says
    the smaller name. Natural Earth files both as a Plateau, so class is no
    guide — size is."""
    n = len(ring)
    if n < 3:
        return 0.0
    a = 0.0
    for k in range(n):
        lo0, la0 = ring[k]
        lo1, la1 = ring[(k + 1) % n]
        a += lo0 * la1 - lo1 * la0
    mid = sum(p[1] for p in ring) / n
    return abs(a) / 2.0 * max(0.05, math.cos(math.radians(mid)))


import math
from eu_boxes import EU_BOXES

entries = []
for f in ne["features"]:
    if f["properties"].get("featurecla") not in NAME_CLASSES:
        continue
    nm = f["properties"].get("name") or f["properties"].get("namealt")
    if not nm:
        continue
    label = nm.title() if nm.isupper() else nm
    for r in geom_rings(f["geometry"]):
        entries.append((r, label))
entries += [([(lo0, la0), (lo1, la0), (lo1, la1), (lo0, la1)], label)
            for label, la0, la1, lo0, lo1 in EU_BOXES]
entries += [(ring, label) for label, _t, ring in REGIONS]
entries.sort(key=lambda rl: -ring_area(rl[0]))


def paint(pairs):
    """pairs of (ring, name-index); a uint16 grid, two 8-bit passes."""
    rings = [r for r, _ in pairs]
    lo = rasterise(rings, [v & 0xFF for _, v in pairs])
    hi = rasterise(rings, [(v >> 8) & 0xFF for _, v in pairs])
    return (hi.astype(np.uint16) << 8) | lo.astype(np.uint16)


layers = [paint([(r, name_id(l)) for r, l in entries])]

namegrid = np.zeros((H, W), dtype=np.uint16)
for g in layers:
    namegrid = np.where(g > 0, g, namegrid)

# ── whatever is still nameless takes the name of the country around it ─────
# "Open Country" is honest but dull, and there is a great deal of it. Every
# place in the gazetteer carries the province and country it sits in, so the
# nearest one lends its name to the empty ground.
import math
places = json.load(open("places_all.json"))
cells = np.argwhere((namegrid == 0) & (land == 1))
if len(cells):
    grid = {}
    for _n, la, lo, _e, rg, _k, _a, pop in places:
        if pop < 500:
            continue
        key = (int(math.floor(la / 2)), int(math.floor(lo / 2)))
        grid.setdefault(key, []).append((la, lo, rg))
    cache = {}
    for j, i in cells:
        la = 90 - (j + 0.5) * RES
        lo = -180 + (i + 0.5) * RES
        key = (int(math.floor(la / 2)), int(math.floor(lo / 2)))
        got = cache.get(key)
        if got is None:
            near = []
            for dj in (-1, 0, 1):
                for di in (-1, 0, 1):
                    near += grid.get((key[0] + dj, key[1] + di), ())
            got = near
            cache[key] = got
        if not got:
            continue
        best, bd = None, 1e18
        k = math.cos(math.radians(la))
        for pla, plo, rg in got:
            d = (pla - la) ** 2 + ((plo - lo) * k) ** 2
            if d < bd:
                best, bd = rg, d
        if best and bd < 9.0:
            namegrid[j, i] = name_id(best)

namegrid[land == 0] = 0

np.save("terrain_0p1.npy", terr)
np.save("names_0p1.npy", namegrid)
json.dump(names, open("names.json", "w"))
import collections
cnt = collections.Counter(terr[land == 1].ravel().tolist())
print("names:", len(names))
for i, c in cnt.most_common():
    print(f"   {TERRAINS[i]:15} {100*c/land.sum():5.1f}%")
