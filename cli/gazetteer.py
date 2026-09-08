"""Places and ground.

The gazetteer is GeoNames' cities1000 — every settlement above a thousand
people, about 171,000 of them — plus the ranges, passes, parks and rivers a
journey gets described by, which GeoNames has no populated place for.

The ground is a 0.1-degree grid (about 11 km) built from ETOPO relief and
Natural Earth's coastline and named regions. It replaced a hand-drawn set of
boxes and polygons: those were adequate for Europe at close range and, at
continental scale, a rectangle over the Rockies also covered Kansas.
"""
import difflib
import json
import os
import re
import unicodedata

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

with open(os.path.join(DATA, "grids.json")) as fh:
    _G = json.load(fh)
RES, GW, GH = _G["res"], _G["w"], _G["h"]

TERRAINS = ["plain","farmland","river_plain","river_valley","steppe_plain","steppe_plateau",
            "coastal","coastal_karst","hills","upland","forest_plain","forest_hills",
            "forest_upland","marsh_plain","mountain","high_mountain","savanna","desert",
            "sand_sea","rainforest","taiga","tundra","high_plateau","open_water"]
NAME_TABLE = _G["nameTable"]


def _expand(vals, lens):
    out = bytearray(GW * GH)
    at = 0
    for v, n in zip(vals, lens):
        if v:
            out[at:at+n] = bytes([v]) * n
        at += n
    return out


def _expand_land(lens):
    out = bytearray(GW * GH)
    at, val = 0, 0
    for n in lens:
        if val:
            out[at:at+n] = b"\x01" * n
        at += n
        val ^= 1
    return out


LAND = _expand_land(_G["land"])
TERRAIN_GRID = _expand(*_G["terrain"])
COMP_GRID = _expand(*_G["comps"])   # which walkable landmass each cell belongs to
_nv, _nl = _G["names"]
NAME_GRID = array_names = None
_names = [0] * (GW * GH)
_at = 0
for _v, _n in zip(_nv, _nl):
    if _v:
        for _k in range(_at, _at + _n):
            _names[_k] = _v
    _at += _n
NAME_GRID = _names
del _names, _nv, _nl


def cell_index(lat, lon):
    j = min(GH - 1, max(0, int((90 - lat) / RES)))
    i = int((lon + 180) / RES) % GW
    return j * GW + i


def is_land(lat, lon):
    return LAND[cell_index(lat, lon)] == 1


def landmass(lat, lon):
    """Which walkable landmass a point sits on. 0 is water; 255 means a speck
    too small to have earned its own number. Two places with different numbers
    cannot be walked between, whatever route you try."""
    return COMP_GRID[cell_index(lat, lon)]


def zone_at(lat, lon):
    k = cell_index(lat, lon)
    terr = TERRAINS[TERRAIN_GRID[k]]
    name = NAME_TABLE[NAME_GRID[k]] if NAME_GRID[k] else "Open Country"
    if terr == "open_water":
        return "Open Water", "open_water"
    return name, terr


# ── places ────────────────────────────────────────────────────────────────
KINDS = {"c":"city","t":"town","r":"range","p":"park","f":"forest","s":"pass",
         "w":"water","n":"plain","o":"coast","u":"custom"}
with open(os.path.join(DATA, "regions_table.json")) as fh:
    REGION_TABLE = json.load(fh)

NAMES, LATS, LONS, REGS, POPS, KIND, ALIAS = [], [], [], [], [], [], []
with open(os.path.join(DATA, "places.tsv"), encoding="utf-8") as fh:
    for line in fh:
        f = line.rstrip("\n").split("\t")
        NAMES.append(f[0]); LATS.append(float(f[1])); LONS.append(float(f[2]))
        REGS.append(int(f[3])); POPS.append(int(f[4])); KIND.append(f[5])
        ALIAS.append(f[6] if len(f) > 6 else "")
N = len(NAMES)


def _fold(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", " and ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip()


# name -> the best record for it (rows are already sorted by population)
INDEX = {}
for _i in range(N):
    _k = _fold(NAMES[_i])
    if _k and _k not in INDEX:
        INDEX[_k] = _i
    if ALIAS[_i]:
        for _a in ALIAS[_i].split("|"):
            _fa = _fold(_a)
            if _fa and _fa not in INDEX:
                INDEX[_fa] = _i

# a coarse bucket index, so "what is the nearest town" is not a linear scan
BUCKET = {}
for _i in range(N):
    BUCKET.setdefault((int(LATS[_i]), int(LONS[_i])), []).append(_i)


class PlaceNotFound(Exception):
    def __init__(self, query, suggestions):
        self.query, self.suggestions = query, suggestions
        super().__init__(query)


def _rec(i, how):
    return dict(name=NAMES[i], lat=LATS[i], lon=LONS[i], elev=0,
                region=REGION_TABLE[REGS[i]], kind=KINDS.get(KIND[i], "town"),
                pop=POPS[i], matched_as=how)


_COORD = re.compile(
    r"""^\s*(?:(?P<label>[^@:]+?)\s*[@:]\s*)?
        (?P<lat>[-+]?\d{1,2}(?:\.\d+)?)\s*(?P<ns>[NnSs])?\s*[,; ]\s*
        (?P<lon>[-+]?\d{1,3}(?:\.\d+)?)\s*(?P<ew>[EeWw])?\s*$""", re.VERBOSE)


def parse_coords(text):
    m = _COORD.match(str(text))
    if not m:
        return None
    lat, lon = float(m.group("lat")), float(m.group("lon"))
    if (m.group("ns") or "").lower() == "s":
        lat = -abs(lat)
    if (m.group("ew") or "").lower() == "w":
        lon = -abs(lon)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return (m.group("label") or "").strip(), lat, lon


def resolve(query):
    raw = str(query).strip()
    if not raw:
        raise PlaceNotFound(raw, [])
    c = parse_coords(raw)
    if c:
        label, lat, lon = c
        return dict(name=label or f"{lat:.3f}, {lon:.3f}", lat=lat, lon=lon, elev=0,
                    region=zone_at(lat, lon)[0], kind="coords", pop=0,
                    matched_as="coordinates")

    q = _fold(raw)
    if q in INDEX:
        return _rec(INDEX[q], "name")

    segs = [_fold(s) for s in re.split(r"[,/]", raw) if _fold(s)]
    # "Raleigh, North Carolina" - try the whole thing, then the leading part
    for cut in range(len(segs), 0, -1):
        j = " ".join(segs[:cut])
        if j in INDEX:
            return _rec(INDEX[j], "name")
    if segs:
        # the first segment names the place; the rest should agree with its region
        head = segs[0]
        if head in INDEX:
            tail = " ".join(segs[1:])
            if tail:
                best = None
                for i in range(N):
                    if _fold(NAMES[i]) == head and tail in _fold(REGION_TABLE[REGS[i]]):
                        best = i
                        break
                if best is not None:
                    return _rec(best, "name and region")
            return _rec(INDEX[head], "name")

    best, score = None, 0.0
    for cand in [q] + segs:
        for key, i in INDEX.items():
            if len(key) < 4:
                continue
            if key in cand:
                s = len(key) / max(len(cand), 1) + 0.5
            elif cand in key and len(cand) >= 4:
                s = len(cand) / len(key)
            else:
                continue
            s += min(POPS[i], 2_000_000) / 20_000_000.0
            if s > score:
                best, score = i, s
    if best is not None and score >= 0.45:
        return _rec(best, "partial name")

    raise PlaceNotFound(raw, suggest(raw))


def suggest(query, n=6):
    q = _fold(query)
    pool = [k for k in INDEX if abs(len(k) - len(q)) <= 4]
    near = difflib.get_close_matches(q, pool, n=n * 4, cutoff=0.62)
    near.sort(key=lambda k: -POPS[INDEX[k]])
    out, seen = [], set()
    for k in near:
        nm = NAMES[INDEX[k]]
        if nm not in seen:
            seen.add(nm)
            out.append(nm)
    return out[:n]


def nearest_place(lat, lon, min_pop=0):
    import math
    best, bd = None, 1e18
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            for i in BUCKET.get((int(lat) + dj, int(lon) + di), ()):
                if POPS[i] < min_pop:
                    continue
                d = (LATS[i] - lat) ** 2 + ((LONS[i] - lon) * math.cos(math.radians(lat))) ** 2
                if d < bd:
                    best, bd = i, d
    if best is None:
        return None, 1e9
    return NAMES[best], math.sqrt(bd) * 111.32


# kept so the rest of the model needs no changes
PLACES = {}
def resolve_city(name):
    r = resolve(name)
    return r["name"], r["lat"], r["lon"], r["elev"]
