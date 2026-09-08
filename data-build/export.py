"""Emit everything the engines need: places, grids, and drawable coastline."""
import json, numpy as np, math
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _os.path.join(_HERE, "..", "cli"))
# Where the downloaded source datasets live. Override with WAYFARE_SOURCES.
SRC = _os.environ.get("WAYFARE_SOURCES", _os.path.join(_HERE, "sources"))
OUT = _os.path.join(_HERE, "..", "data")   # the four files the app and the CLI read

# ── places ────────────────────────────────────────────────────────────────
P = json.load(open("places_all.json"))
# drop curated duplicates of a GeoNames town
geo = {}
for r in P:
    if r[7] > 0 or r[5] in ("city", "town"):
        geo.setdefault(r[0].lower(), []).append(r)
keep, dropped = [], 0
for r in P:
    if r[7] == 0 and r[5] in ("city", "town"):
        near = [g for g in geo.get(r[0].lower(), [])
                if g is not r and abs(g[1]-r[1]) < 0.25 and abs(g[2]-r[2]) < 0.25]
        if near:
            dropped += 1
            continue
    keep.append(r)
P = keep
# rank, not raw population, decides which Orleans you get when you type Orleans
P.sort(key=lambda r: -(r[8] if len(r) > 8 else r[7]))
print(f"places {len(P):,} (dropped {dropped} curated duplicates)")

# regions are interned: a hundred and seventy thousand copies of "United States"
# is a megabyte of nothing
REG, RIX = [], {}
def reg_id(name):
    if name not in RIX:
        RIX[name] = len(REG)
        REG.append(name)
    return RIX[name]

lines = []
for name, la, lo, el, rg, kind, al, pop, *_rank in P:
    row = [name, f"{la:.3f}".rstrip("0").rstrip("."), f"{lo:.3f}".rstrip("0").rstrip("."),
           str(reg_id(rg)), str(pop), kind[0]]
    if al:
        row.append(al)
    lines.append("\t".join(row))
blob = "\n".join(lines)
open(_os.path.join(OUT, "places.tsv"), "w").write(blob)
open(_os.path.join(OUT, "regions_table.json"), "w").write(json.dumps(REG, ensure_ascii=False, separators=(",", ":")))
print("regions", len(REG))
print("places.tsv", f"{len(blob):,} bytes")

# ── grids, run-length encoded ─────────────────────────────────────────────
def rle(a):
    flat = a.reshape(-1)
    change = np.flatnonzero(np.diff(flat)) + 1
    bounds = np.concatenate(([0], change, [flat.size]))
    lens = np.diff(bounds).tolist()
    vals = flat[bounds[:-1]].tolist()
    return vals, lens

land = np.load("landmask_0p1.npy")
terr = np.load("terrain_0p1.npy")
namg = np.load("names_0p1.npy")
comps = np.load("comps_0p1.npy")
names = json.load(open("names.json"))

lvals, llens = rle(land)
tvals, tlens = rle(terr)
nvals, nlens = rle(namg)
cvals, clens = rle(comps)
print("runs: land", f"{len(llens):,}", "terrain", f"{len(tlens):,}", "names", f"{len(nlens):,}", "comps", f"{len(clens):,}")

grids = {
  "res": 0.1, "w": land.shape[1], "h": land.shape[0],
  "land": llens,                       # starts sea, alternates
  "terrain": [tvals, tlens],
  "names": [nvals, nlens],
  "comps": [cvals, clens],
  "nameTable": names,
}
open(_os.path.join(OUT, "grids.json"), "w").write(json.dumps(grids, separators=(",", ":"), ensure_ascii=False))
print("grids.json", f"{len(open(_os.path.join(OUT, 'grids.json')).read()):,} bytes")

# ── coastline for drawing, simplified ─────────────────────────────────────
def simplify(ring, tol):
    if len(ring) < 4: return ring
    keep = [0, len(ring)-1]
    stack = [(0, len(ring)-1)]
    kept = set(keep)
    while stack:
        lo, hi = stack.pop()
        if hi <= lo+1: continue
        ax, ay = ring[lo]; bx, by = ring[hi]
        worst, wi = -1, -1
        dx, dy = bx-ax, by-ay
        L = dx*dx + dy*dy
        for k in range(lo+1, hi):
            px, py = ring[k]
            t = 0 if L == 0 else max(0, min(1, ((px-ax)*dx + (py-ay)*dy)/L))
            d = (px-ax-t*dx)**2 + (py-ay-t*dy)**2
            if d > worst: worst, wi = d, k
        if worst > tol*tol:
            kept.add(wi); stack.append((lo, wi)); stack.append((wi, hi))
    return [ring[i] for i in sorted(kept)]

def rings(g):
    t, c = g["type"], g["coordinates"]
    return [c] if t == "Polygon" else c if t == "MultiPolygon" else []

def collect(path, tol, min_pts):
    out = []
    for f in json.load(open(path))["features"]:
        for poly in rings(f["geometry"]):
            for ring in poly:
                s = simplify([(round(x,3), round(y,3)) for x, y in ring], tol)
                if len(s) >= min_pts:
                    out.append([v for p in s for v in p])
    return out

coast = collect(f"{SRC}/ne_10m_land.json", 0.06, 5)
lakes = collect(f"{SRC}/ne_10m_lakes.json", 0.06, 5)
print("drawable rings: land", len(coast), "lakes", len(lakes))
open(_os.path.join(OUT, "coastline.json"), "w").write(json.dumps({"land": coast, "lakes": lakes}, separators=(",", ":")))
print("coastline.json", f"{len(open(_os.path.join(OUT, 'coastline.json')).read()):,} bytes")
