#!/usr/bin/env python3
"""Middle-earth, at a tenth of a degree.

    python3 data-build/build_middle_earth.py

Turns the ME-DEM team's GIS layers into the same four files the app and the
CLI read for the real world, written to `data/middle-earth/`:

    grids.json          land, terrain, region name and landmass, run-length
                        encoded on the same 3600 x 1800 frame as the earth's
    coastline.json      drawable land and lake rings
    places.tsv          the gazetteer, sorted by rank
    regions_table.json  the interned "Province, Country" strings

Sources, expected under `data-build/sources/middle-earth/` (see README):

    ME-GIS/             the shapefiles — coastline, lakes, forests, wetlands,
                        and the 785 named points
    10k.jpg, 10k.wld    the 10,000-pixel elevation model from the Arda repo,
                        one byte per pixel, and the world file that places it

## Where Middle-earth is

The shapefiles are in a map frame of metres, two thousand kilometres a side,
that a GIS was told to call UTM zone 31 so that it would behave. Measured
against Tolkien's own distances — Hobbiton to Rivendell is 458 miles in
Fonstad's atlas, and here it is 368 km — the frame is at half scale, so every
coordinate is doubled. Tolkien also said where Middle-earth sits: Hobbiton is
at about the latitude of Oxford, Minas Tirith at about Florence's. Doubling
the frame and pinning Hobbiton to Oxford puts Minas Tirith at 44.2°N, which is
Florence to within half a degree, and that is the projection used here: a
plain kilometre grid laid on the globe around the Shire. Daylight in the
model comes from latitude, so the Shire's summer evenings are long and
Forochel's winter days are short, as they should be.

## What the elevation model means

The DEM is a JPEG of bytes. Read against the contour layer, byte 16 is sea
level, the bytes below it are bathymetry, and the bytes above climb with a
curve that flattens towards the peaks — a hundred and forty-five is about
4,500 m. `BYTE_TO_M` is that curve, read off the contours' median byte.

Land is whatever the sea cannot reach: the ocean is flooded inward from the
edge of the map through every byte at or below sea level, and everything else
is ground — including the inland seas, which the lake layer then takes back.

## What the ground is

Ruggedness is classed exactly as it is for the earth in `terrain.py`: local
relief within a cell and mean elevation, at the same thresholds. Biome is
simpler than the earth's because the ME-DEM team drew the forests and marshes
by hand, so those are read straight from the layers; the settled country, the
grasslands, the deserts and the far north come from `me_regions.py`, which is
also where the names of the countries live.
"""
import collections
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

try:
    import shapefile          # pyshp
except ImportError:
    sys.exit("needs pyshp:  pip install pyshp")

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SRC = os.environ.get("WAYFARE_ME_SOURCES", os.path.join(HERE, "sources", "middle-earth"))
GIS = os.path.join(SRC, "ME-GIS")
OUT = os.path.join(HERE, "..", "data", "middle-earth")
os.makedirs(OUT, exist_ok=True)

from me_regions import REGIONS          # noqa: E402
from me_places import RENAME, ALIASES, EXTRA   # noqa: E402

# ── the frame ─────────────────────────────────────────────────────────────
RES = 0.1
W, H = int(360 / RES), int(180 / RES)
SCALE = 2.0                          # the shapefiles' km, doubled
HOBBITON = (515948.0, 1043820.0)     # in the shapefiles' metres
HOBBITON_LL = (51.75, -1.26)         # Oxford
M_PER_DEG = 111320.0


def to_ll(x, y):
    """shapefile metres -> (lat, lon)"""
    lat = HOBBITON_LL[0] + SCALE * (y - HOBBITON[1]) / M_PER_DEG
    lon = HOBBITON_LL[1] + SCALE * (x - HOBBITON[0]) / (M_PER_DEG * np.cos(np.radians(lat)))
    return lat, lon


def to_xy(lat, lon):
    """(lat, lon) -> shapefile metres"""
    y = HOBBITON[1] + (lat - HOBBITON_LL[0]) * M_PER_DEG / SCALE
    x = HOBBITON[0] + (lon - HOBBITON_LL[1]) * M_PER_DEG * np.cos(np.radians(lat)) / SCALE
    return x, y


# ── the elevation model ───────────────────────────────────────────────────
wld = [float(v) for v in open(os.path.join(SRC, "10k.wld")).read().split()]
PX, X0, Y0 = wld[0], wld[4], wld[5]         # metres per pixel; top-left corner
dem = np.array(Image.open(os.path.join(SRC, "10k.jpg")).convert("L"))
N = dem.shape[0]
dem[dem >= 250] = 0                          # the frame round the edge is not ground
K = 4                                        # work at 800 m: plenty for an 11 km cell
n = N // K
D = dem[:n * K, :n * K].reshape(n, K, n, K).mean(axis=(1, 3))
PXK = PX * K
print(f"DEM {N}x{N} at {PX:.1f} m, reduced to {n}x{n}")

SEA_BYTE = 16.5
BYTE_TO_M = [(0, -450), (16, 0), (20, 38), (24, 76), (28, 114), (32, 152), (36, 229),
             (42, 305), (49, 457), (52, 610), (55, 762), (65, 914), (73, 1219),
             (89, 1524), (95, 1829), (99, 2134), (103, 2743), (112, 3048),
             (122, 3658), (133, 4267), (145, 4572), (170, 5200), (254, 7000)]
ELEV = np.interp(D, [b for b, _ in BYTE_TO_M], [m for _, m in BYTE_TO_M])

# the ocean: flood inward from the edge through everything at or below sea level
img = Image.fromarray(np.where(D <= SEA_BYTE, 0, 128).astype(np.uint8)).convert("L")
ImageDraw.floodfill(img, (0, 0), 255)
OCEAN = np.array(img) == 255
print(f"ocean {100 * OCEAN.mean():.1f}% of the frame; "
      f"{100 * ((D <= SEA_BYTE) & ~OCEAN).mean():.2f}% is low ground the sea cannot reach")


def px_of(x, y):
    return (x - X0) / PXK, (Y0 - y) / PXK


def reader(name):
    return shapefile.Reader(os.path.join(GIS, name), encoding="latin-1")


def paint_polys(name, fill_by_record=None, base=0):
    """A shapefile of polygons rasterised onto the reduced DEM frame."""
    im = Image.new("L", (n, n), base)
    d = ImageDraw.Draw(im)
    r = reader(name)
    for rec, shp in zip(r.records(), r.shapes()):
        v = 1 if fill_by_record is None else fill_by_record(rec)
        if v is None:
            continue
        parts = list(shp.parts) + [len(shp.points)]
        for a, b in zip(parts[:-1], parts[1:]):
            pts = [px_of(x, y) for x, y in shp.points[a:b]]
            if len(pts) >= 3:
                d.polygon(pts, fill=v)
    return np.array(im)


LAKE = paint_polys("Lakes.shp") == 1
FOREST = paint_polys("Forests.shp",
                     lambda rec: 1 if (rec["TYPE"] or "").strip() == "Deciduous Forest" else
                                 (2 if (rec["TYPE"] or "").strip() == "Forest Clearing" else None)) == 1
WET = paint_polys("Wetlands02.shp") == 1
print(f"lakes {LAKE.sum():,} px, forest {FOREST.sum():,} px, wetland {WET.sum():,} px")

# ── the frame's footprint on the globe ────────────────────────────────────
corners = [to_ll(x, y) for x in (0, N * PX) for y in (0, N * PX)]
LAT0, LAT1 = min(c[0] for c in corners), max(c[0] for c in corners)
LON0, LON1 = min(c[1] for c in corners), max(c[1] for c in corners)
J0, J1 = int((90 - LAT1) / RES), int((90 - LAT0) / RES) + 1
I0, I1 = int((LON0 + 180) / RES), int((LON1 + 180) / RES) + 1
print(f"footprint lat {LAT0:.1f}..{LAT1:.1f}, lon {LON0:.1f}..{LON1:.1f}: "
      f"cells rows {J0}..{J1}, cols {I0}..{I1}")

# ── sampling every cell ───────────────────────────────────────────────────
S = 6                                    # 36 samples per cell, 1.9 km apart
sub = (np.arange(S) + 0.5) / S - 0.5
jj, ii = np.meshgrid(np.arange(J0, J1), np.arange(I0, I1), indexing="ij")
lat_c = 90 - (jj + 0.5) * RES
lon_c = -180 + (ii + 0.5) * RES
lat_s = lat_c[..., None, None] - sub[None, None, :, None] * RES
lon_s = lon_c[..., None, None] + sub[None, None, None, :] * RES
xs, ys = to_xy(lat_s, lon_s)
px, py = px_of(xs, ys)
inside = (px >= 0) & (px < n) & (py >= 0) & (py < n)
pi = np.clip(px.astype(int), 0, n - 1)
pj = np.clip(py.astype(int), 0, n - 1)


def sample(grid, fill):
    v = grid[pj, pi]
    return np.where(inside, v, fill)


ocean_s = sample(OCEAN, True)
lake_s = sample(LAKE, False)
elev_s = np.where(sample(OCEAN, True), 0.0, sample(ELEV, 0.0))
forest_s = sample(FOREST, False)
wet_s = sample(WET, False)

land_frac = (~ocean_s & ~lake_s).mean(axis=(2, 3))
LANDC = land_frac >= 0.5
elev = elev_s.mean(axis=(2, 3))
relief = elev_s.max(axis=(2, 3)) - elev_s.min(axis=(2, 3))
forestc = forest_s.mean(axis=(2, 3)) >= 0.5
wetc = wet_s.mean(axis=(2, 3)) >= 0.4
print(f"land cells {LANDC.sum():,}; forest {forestc[LANDC].sum():,}, wetland {wetc[LANDC].sum():,}")

# ── the regions, painted onto the same window ─────────────────────────────
TERRAINS = ["plain", "farmland", "river_plain", "river_valley", "steppe_plain", "steppe_plateau",
            "coastal", "coastal_karst", "hills", "upland", "forest_plain", "forest_hills",
            "forest_upland", "marsh_plain", "mountain", "high_mountain", "savanna", "desert",
            "sand_sea", "rainforest", "taiga", "tundra", "high_plateau", "open_water"]
TI = {t: i for i, t in enumerate(TERRAINS)}
WH, WW = J1 - J0, I1 - I0


def ring_ll(ring_km):
    return [to_ll(x * 1000.0, y * 1000.0) for x, y in ring_km]


def area_deg2(ring):
    a = 0.0
    for k in range(len(ring)):
        la0, lo0 = ring[k]
        la1, lo1 = ring[(k + 1) % len(ring)]
        a += lo0 * la1 - lo1 * la0
    return abs(a) / 2


regions = [(label, parent, terr, ring_ll(ring)) for label, parent, terr, ring in REGIONS]
regions.sort(key=lambda r: -area_deg2(r[3]))      # big first, so small paints last


def paint_window(pairs):
    im = Image.new("I", (WW, WH), 0)
    d = ImageDraw.Draw(im)
    for ring, v in pairs:
        d.polygon([((lo + 180) / RES - I0, (90 - la) / RES - J0) for la, lo in ring], fill=int(v))
    return np.array(im)


names = ["Open Country"]
region_str = [""]
region_of_label = {}
for label, parent, _t, _r in regions:
    if label not in names:
        names.append(label)
        region_str.append(f"{label}, {parent}" if parent else label)
        region_of_label[label] = region_str[-1]
NAMEW = paint_window([(ring, names.index(label)) for label, _p, _t, ring in regions])
BIOW = paint_window([(ring, TI[terr] + 1) for _l, _p, terr, ring in regions if terr])

# whatever the polygons leave nameless takes the nearest area label in the layer
pl = reader("Combined_Placenames.shp")
labels = []
for rec, shp in zip(pl.records(), pl.shapes()):
    nm = rec["NAME"].strip()
    if rec["LAYER"] in ("GeographicAreaNames", "HillsNames", "MoorsNames", "PlainsNames") and nm:
        nm = RENAME.get(nm, nm)
        la, lo = to_ll(*shp.points[0])
        labels.append((la, lo, nm))
nameless = np.argwhere((NAMEW == 0) & LANDC)
filled = 0
for j, i in nameless:
    la, lo = 90 - (J0 + j + 0.5) * RES, -180 + (I0 + i + 0.5) * RES
    k = math.cos(math.radians(la))
    best, bd = None, 1e9
    for pla, plo, nm in labels:
        d = (pla - la) ** 2 + ((plo - lo) * k) ** 2
        if d < bd:
            best, bd = nm, d
    if best and bd < 1.6 ** 2:                   # within about 180 km
        if best not in names:
            names.append(best)
            region_str.append(best)
        NAMEW[j, i] = names.index(best)
        filled += 1
print(f"names: {len(names)} ({filled:,} cells took the nearest label)")

# ── terrain ───────────────────────────────────────────────────────────────
FLAT, HILL, UP, MTN, HIGH = 0, 1, 2, 3, 4
rug = np.zeros((WH, WW), dtype=np.uint8)
rug[relief >= 150] = HILL
rug[relief >= 350] = UP
rug[relief >= 700] = MTN
rug[((relief >= 1150) & (elev >= 1700)) | (elev >= 3000)] = HIGH

hand = np.where(BIOW > 0, BIOW - 1, 255).astype(np.uint8)   # a terrain index, or 255
lat2d = lat_c
biome = np.full((WH, WW), "temperate", dtype=object)
biome[lat2d >= 57.5] = "taiga"
biome[lat2d >= 63.0] = "tundra"
biome[lat2d <= 37.0] = "dry"
settled = hand == TI["farmland"]
for t, b in (("steppe_plain", "steppe"), ("steppe_plateau", "steppe"), ("desert", "desert"),
             ("savanna", "savanna"), ("tundra", "tundra"), ("taiga", "taiga")):
    biome[hand == TI[t]] = b
biome[forestc] = np.where(np.isin(biome[forestc], ["tundra"]), "taiga", "forest")
biome[wetc] = "marsh"

flat = {"temperate": "plain", "forest": "forest_plain", "marsh": "marsh_plain", "steppe": "steppe_plain",
        "desert": "desert", "savanna": "savanna", "taiga": "taiga", "tundra": "tundra", "dry": "steppe_plain"}
hill = {"temperate": "hills", "forest": "forest_hills", "marsh": "hills", "steppe": "hills",
        "desert": "desert", "savanna": "hills", "taiga": "forest_hills", "tundra": "tundra", "dry": "hills"}
upl = {"temperate": "upland", "forest": "forest_upland", "marsh": "upland", "steppe": "steppe_plateau",
       "desert": "steppe_plateau", "savanna": "upland", "taiga": "forest_upland", "tundra": "tundra",
       "dry": "steppe_plateau"}
terr = np.full((WH, WW), TI["open_water"], dtype=np.uint8)
for b in flat:
    terr[(rug == FLAT) & (biome == b)] = TI[flat[b]]
    terr[(rug == HILL) & (biome == b)] = TI[hill[b]]
    terr[(rug == UP) & (biome == b)] = TI[upl[b]]
terr[(rug == FLAT) & settled] = TI["farmland"]
terr[rug == MTN] = TI["mountain"]
terr[rug == HIGH] = TI["high_mountain"]
terr[(elev >= 2600) & (relief < 900)] = TI["high_plateau"]
# a region drawn as a particular kind of ground is that ground, short of a range
direct = [t for t in ("high_plateau", "upland", "hills", "forest_hills", "forest_plain", "marsh_plain")]
for t in direct:
    m = (hand == TI[t]) & (rug < MTN)
    if t == "high_plateau":
        m = (hand == TI[t]) & (rug < HIGH)
    terr[m] = TI[t]
terr[~LANDC] = TI["open_water"]

cnt = collections.Counter(terr[LANDC].ravel().tolist())
for i, c in cnt.most_common():
    print(f"   {TERRAINS[i]:15} {100 * c / LANDC.sum():5.1f}%")

# ── landmasses ────────────────────────────────────────────────────────────
comp = np.zeros((WH, WW), dtype=np.int32)
sizes = [0]
cid = 0
for j in range(WH):
    for i in range(WW):
        if not LANDC[j, i] or comp[j, i]:
            continue
        cid += 1
        q = collections.deque([(i, j)])
        comp[j, i] = cid
        m = 0
        while q:
            ci, cj = q.popleft()
            m += 1
            for dj in (-1, 0, 1):
                for di in (-1, 0, 1):
                    ni, nj = ci + di, cj + dj
                    if 0 <= ni < WW and 0 <= nj < WH and LANDC[nj, ni] and not comp[nj, ni]:
                        comp[nj, ni] = cid
                        q.append((ni, nj))
        sizes.append(m)
order = sorted(range(1, cid + 1), key=lambda k: -sizes[k])
remap = np.zeros(cid + 1, dtype=np.uint8)
for rank, k in enumerate(order):
    remap[k] = (rank + 1) if rank < 254 else 255
compw = remap[comp]
print(f"{cid} landmasses; the mainland is {sizes[order[0]]:,} cells "
      f"({100 * sizes[order[0]] / LANDC.sum():.1f}% of land)")

# ── onto the full frame, run-length encoded ───────────────────────────────
land_full = np.zeros((H, W), dtype=np.uint8)
terr_full = np.full((H, W), TI["open_water"], dtype=np.uint8)
name_full = np.zeros((H, W), dtype=np.uint16)
comp_full = np.zeros((H, W), dtype=np.uint8)
land_full[J0:J1, I0:I1] = LANDC
terr_full[J0:J1, I0:I1] = terr
name_full[J0:J1, I0:I1] = np.where(LANDC, NAMEW, 0)
comp_full[J0:J1, I0:I1] = compw


def rle(a):
    flat_ = a.reshape(-1)
    change = np.flatnonzero(np.diff(flat_)) + 1
    bounds = np.concatenate(([0], change, [flat_.size]))
    return flat_[bounds[:-1]].tolist(), np.diff(bounds).tolist()


lvals, llens = rle(land_full)
if lvals and lvals[0] != 0:
    llens = [0] + llens
grids = {
    "res": RES, "w": W, "h": H,
    "land": llens,
    "terrain": list(rle(terr_full)),
    "names": list(rle(name_full)),
    "comps": list(rle(comp_full)),
    "nameTable": names,
}
gpath = os.path.join(OUT, "grids.json")
open(gpath, "w").write(json.dumps(grids, separators=(",", ":"), ensure_ascii=False))
print("grids.json", f"{os.path.getsize(gpath):,} bytes")


# ── the coast, traced ─────────────────────────────────────────────────────
def trace(mask):
    """Rings round every region of a binary raster, as pixel-corner loops."""
    m = np.pad(mask, 1).astype(np.uint8)
    hh, ww = m.shape
    edges = {}
    # each land pixel contributes an edge on every side that faces water,
    # oriented so the loops close head to tail
    r, c = np.nonzero(m[1:-1, 1:-1])
    r += 1; c += 1
    top = m[r - 1, c] == 0
    right = m[r, c + 1] == 0
    bottom = m[r + 1, c] == 0
    left = m[r, c - 1] == 0
    key = lambda x, y: y * (ww + 1) + x

    def add(rs, cs, x0, y0, x1, y1):
        for x, y in zip(cs, rs):
            edges.setdefault(key(x + x0, y + y0), []).append(key(x + x1, y + y1))
    add(r[top], c[top], 0, 0, 1, 0)
    add(r[right], c[right], 1, 0, 1, 1)
    add(r[bottom], c[bottom], 1, 1, 0, 1)
    add(r[left], c[left], 0, 1, 0, 0)
    rings = []
    while edges:
        start, outs = next(iter(edges.items()))
        ring = [start]
        cur = start
        while True:
            outs = edges.get(cur)
            if not outs:
                break
            nxt = outs.pop()
            if not outs:
                del edges[cur]
            ring.append(nxt)
            cur = nxt
            if cur == start:
                break
        rings.append([(k % (ww + 1) - 1, k // (ww + 1) - 1) for k in ring])
    return rings


def simplify(ring, tol):
    if len(ring) < 4:
        return ring
    kept = {0, len(ring) - 1}
    stack = [(0, len(ring) - 1)]
    while stack:
        lo, hi = stack.pop()
        if hi <= lo + 1:
            continue
        ax, ay = ring[lo]; bx, by = ring[hi]
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy
        worst, wi = -1, -1
        for k in range(lo + 1, hi):
            x, y = ring[k]
            t = 0 if L == 0 else max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / L))
            d = (x - ax - t * dx) ** 2 + (y - ay - t * dy) ** 2
            if d > worst:
                worst, wi = d, k
        if worst > tol * tol:
            kept.add(wi); stack.append((lo, wi)); stack.append((wi, hi))
    return [ring[i] for i in sorted(kept)]


def ring_to_flat(ring_ll_, tol, min_pts):
    s = simplify([(round(lo, 3), round(la, 3)) for la, lo in ring_ll_], tol)
    if len(s) < min_pts:
        return None
    return [v for p in s for v in p]


land_rings = trace(~OCEAN)
coast = []
for ring in land_rings:
    if len(ring) < 12:
        continue
    ll = [to_ll(X0 + x * PXK, Y0 - y * PXK) for x, y in ring]
    f = ring_to_flat(ll, 0.025, 5)
    if f:
        coast.append(f)
lakes = []
lk = reader("Lakes.shp")
for shp in lk.shapes():
    parts = list(shp.parts) + [len(shp.points)]
    for a, b in zip(parts[:-1], parts[1:]):
        ll = [to_ll(x, y) for x, y in shp.points[a:b]]
        f = ring_to_flat(ll, 0.012, 5)
        if f:
            lakes.append(f)
cpath = os.path.join(OUT, "coastline.json")
open(cpath, "w").write(json.dumps({"land": coast, "lakes": lakes}, separators=(",", ":")))
print(f"drawable rings: land {len(coast)} ({sum(len(c) // 2 for c in coast):,} points), lakes {len(lakes)}; "
      f"coastline.json {os.path.getsize(cpath):,} bytes")

# ── the gazetteer ─────────────────────────────────────────────────────────
KIND = {"CityNames": "c", "CitadelNames": "k", "TownNames": "t", "VillageNames": "t",
        "ManorHouseNames": "t", "TowersandKeepsNames": "k", "BeaconNames": "k",
        "RuinNames": "x", "BurialSiteNames": "x", "MountainNames": "r", "HillsNames": "r",
        "VulcanismNames": "r", "PlainsNames": "n", "MoorsNames": "n", "GeographicAreaNames": "g",
        "ForestNames": "f", "WetlandNames": "m", "PassNames": "s", "FordsandCrossingsNames": "d",
        "IslandNames": "o", "LakeNames": "w", "RiverNames": "w"}
# rank, not population: what decides which dot is drawn at a given zoom and
# which name a camp is described by. Cities always, ruins only up close.
RANK = {"CityNames": 1000000, "CitadelNames": 250000, "TownNames": 80000, "VillageNames": 20000,
        "ManorHouseNames": 6000, "TowersandKeepsNames": 3000, "BeaconNames": 3000,
        "RuinNames": 3000, "BurialSiteNames": 2000}


def region_at(lat, lon):
    j, i = int((90 - lat) / RES) - J0, int((lon + 180) / RES) - I0
    if 0 <= j < WH and 0 <= i < WW and NAMEW[j, i]:
        return region_str[NAMEW[j, i]]
    return "Middle-earth"


rows = []
seen = set()
for rec, shp in zip(pl.records(), pl.shapes()):
    layer, nm = rec["LAYER"], rec["NAME"].strip()
    if layer not in KIND or not nm:
        continue
    nm = RENAME.get(nm, nm)
    alias = ALIASES.get(nm, "")
    if layer == "RiverNames":
        bare = nm[3:].strip() if nm.startswith("R.") else nm
        nm = "River " + bare
        alias = "|".join(a for a in (bare, alias) if a)
    if layer == "MountainNames" and nm == "Erebor":
        alias = ALIASES["Erebor"]
    la, lo = to_ll(*shp.points[0])
    if (nm, round(la, 1), round(lo, 1)) in seen:
        continue
    seen.add((nm, round(la, 1), round(lo, 1)))
    rows.append((nm, la, lo, region_at(la, lo), RANK.get(layer, 0), KIND[layer], alias))
for nm, xk, yk, kind, rank, alias in EXTRA:
    la, lo = to_ll(xk * 1000.0, yk * 1000.0)
    rows.append((nm, la, lo, region_at(la, lo), rank, kind, alias))
rows.sort(key=lambda r: (-r[4], r[0]))

REG, RIX = [], {}
def reg_id(s):
    if s not in RIX:
        RIX[s] = len(REG); REG.append(s)
    return RIX[s]

lines = []
for nm, la, lo, rg, rank, kind, alias in rows:
    row = [nm, f"{la:.3f}".rstrip("0").rstrip("."), f"{lo:.3f}".rstrip("0").rstrip("."),
           str(reg_id(rg)), str(rank), kind]
    if alias:
        row.append(alias)
    lines.append("\t".join(row))
open(os.path.join(OUT, "places.tsv"), "w", encoding="utf-8").write("\n".join(lines))
open(os.path.join(OUT, "regions_table.json"), "w").write(json.dumps(REG, ensure_ascii=False, separators=(",", ":")))
print(f"places {len(rows)}, regions {len(REG)}")
wet = [r[0] for r in rows if not land_full[int((90 - r[1]) / RES), int((r[2] + 180) / RES)]]
print(f"{len(wet)} places fall in the water at this grain: {wet[:12]}")

# ── a picture, to look at ─────────────────────────────────────────────────
PAL = {"plain": (222, 216, 180), "farmland": (214, 206, 150), "steppe_plain": (205, 199, 156),
       "steppe_plateau": (195, 186, 147), "hills": (188, 176, 130), "upland": (170, 156, 118),
       "forest_plain": (150, 176, 120), "forest_hills": (126, 156, 104), "forest_upland": (104, 136, 92),
       "marsh_plain": (160, 190, 170), "mountain": (150, 140, 130), "high_mountain": (235, 235, 235),
       "desert": (230, 210, 160), "savanna": (215, 205, 140), "taiga": (120, 150, 120),
       "tundra": (200, 205, 200), "high_plateau": (170, 160, 150), "open_water": (207, 220, 224)}
Z = 3
pic = Image.new("RGB", (WW * Z, WH * Z), PAL["open_water"])
d = ImageDraw.Draw(pic)
arr = np.zeros((WH, WW, 3), dtype=np.uint8)
for t, col in PAL.items():
    arr[terr == TI[t]] = col
pic = Image.fromarray(arr).resize((WW * Z, WH * Z), Image.NEAREST)
d = ImageDraw.Draw(pic)
for f in coast:
    pts = [(((f[k] + 180) / RES - I0) * Z, ((90 - f[k + 1]) / RES - J0) * Z) for k in range(0, len(f), 2)]
    d.line(pts + pts[:1], fill=(70, 90, 95), width=1)
for f in lakes:
    pts = [(((f[k] + 180) / RES - I0) * Z, ((90 - f[k + 1]) / RES - J0) * Z) for k in range(0, len(f), 2)]
    if len(pts) > 2:
        d.polygon(pts, fill=PAL["open_water"], outline=(70, 90, 95))
for nm, la, lo, rg, rank, kind, alias in rows:
    if kind == "c" or rank >= 250000:
        x, y = ((lo + 180) / RES - I0) * Z, ((90 - la) / RES - J0) * Z
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(40, 30, 30))
        d.text((x + 3, y - 5), nm, fill=(40, 30, 30))
ppath = os.path.join(HERE, "middle_earth_preview.png")
pic.save(ppath)
print("preview", ppath)
