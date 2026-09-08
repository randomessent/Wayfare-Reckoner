"""Finding a way across land.

Before this existed the model drew a straight line and asked what terrain lay
under it, which is fine until the line crosses the Bay of Biscay. Now an A*
search over the land mask finds a route that stays on the ground — preferring
easy going, and taking to the water only as far as the party's boats allow.

The mask is the 0.1-degree grid built from Natural Earth's coastline, with the
narrow waters a raster welds shut (Gibraltar, the Bosphorus, the Belts) forced
open and the modern canals — Suez, Corinth — forced shut, because in this world
nobody dug them. At 11 km a crossing of Eurasia is far too many cells for one
search, so a long route is found twice: once on a 0.5-degree grid to learn
roughly where the way lies, and then properly, inside a corridor around it.
"""
import heapq
import math

from gazetteer import LAND, COMP_GRID, RES, GW, GH

R_EARTH = 6371.0
MW, MH = GW, GH
BEST_FACTOR = 1.05   # the fastest ground there is; the bound must assume it


def mask():
    return LAND


def cell_of(lat, lon):
    j = min(MH - 1, max(0, int((90 - lat) / RES)))
    i = int((lon + 180) / RES) % MW
    return i, j


def centre(i, j):
    return 90 - (j + 0.5) * RES, -180 + ((i % MW) + 0.5) * RES


def is_land_cell(i, j):
    return LAND[j * MW + (i % MW)] == 1


def hav(a_lat, a_lon, b_lat, b_lon):
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    h = (math.sin((p2-p1)/2)**2
         + math.cos(p1)*math.cos(p2)*math.sin(math.radians(b_lon-a_lon)/2)**2)
    return 2*R_EARTH*math.asin(math.sqrt(min(1.0, h)))


# how attractive water is, by what the party can float on
BOATS = {
    "none":    dict(label="none — they keep their feet dry", water=None, reach=0,
                    note="No crossing of open water at all. If there is no way round, there is no way."),
    "ferries": dict(label="ferry crossings", water=0.16, reach=8, sea_pace=4.0, embark=6.0,
                    note="Boatmen at the narrow places. Straits and river mouths are crossable; "
                         "an open sea is not worth the asking."),
    "ship":    dict(label="a ship", water=0.75, reach=None, sea_pace=6.5, embark=12.0,
                    note="A vessel that will take them along a coast or across a sea, sailing through the night."),
}


# How far from a shore a party will go. A ferryman will put you across a strait
# and will not take you to Greenland, so his water is only the water you can see
# the far side of; a ship's is all of it.
_SHORE = {}


def near_shore(i, j, reach):
    """Is there land within `reach` cells of this water cell?"""
    key = (i, j, reach)
    hit = _SHORE.get(key)
    if hit is None:
        hit = False
        for r in range(1, reach + 1):
            for dj in range(-r, r + 1):
                nj = j + dj
                if nj < 0 or nj >= MH:
                    continue
                span = range(-r, r + 1) if abs(dj) == r else (-r, r)
                for di in span:
                    if LAND[nj * MW + ((i + di) % MW)]:
                        hit = True
                        break
                if hit:
                    break
            if hit:
                break
        if len(_SHORE) > 300000:
            _SHORE.clear()
        _SHORE[key] = hit
    return hit


# ── the coarse grid, for finding roughly where the way lies ────────────────
CF = 5                       # coarse cells are CF fine cells across: 0.5 degrees
CW, CH = MW // CF, MH // CF


def _build_coarse():
    """A coarse cell is land if any fine cell in it is land, so a route that
    must thread a strait still has a corridor to be found in."""
    out = bytearray(CW * CH)
    for j in range(MH):
        row = j * MW
        cj = (j // CF) * CW
        for i in range(MW):
            if LAND[row + i]:
                out[cj + i // CF] = 1
    return out


_COARSE = None


def coarse():
    global _COARSE
    if _COARSE is None:
        _COARSE = _build_coarse()
    return _COARSE


_CACHE = {}


def find(a, b, boat="none", cost_at=None, max_cells=1400000):
    """Cached wrapper — the way over the ground depends only on the two ends
    and what the party can float on, never on how fast they walk."""
    key = (round(a[0], 4), round(a[1], 4), round(b[0], 4), round(b[1], 4), boat)
    if key not in _CACHE:
        if len(_CACHE) > 400:
            _CACHE.clear()
        _CACHE[key] = _find(a, b, boat, cost_at, max_cells)
    return _CACHE[key]


def _astar(start, goal, w, h, passable, heur, max_cells):
    """A* on a lat/lon grid of width w. passable(i, j) -> factor or None,
    heur(i, j) -> a lower bound on the remaining cost. Returns the cell path."""
    res_lat = 180.0 / h
    res_lon = 360.0 / w

    def ctr(i, j):
        return 90 - (j + 0.5) * res_lat, -180 + ((i % w) + 0.5) * res_lon

    g = {start: 0.0}
    came = {}
    heap = [(heur(*start), 0.0, start)]
    seen = set()
    steps = 0
    while heap:
        _f, gc, cur = heapq.heappop(heap)
        if cur in seen:
            continue
        seen.add(cur)
        steps += 1
        if steps > max_cells:
            return None
        if cur == goal:
            break
        ci, cj = cur
        clat, clon = ctr(ci, cj)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di == 0 and dj == 0:
                    continue
                ni, nj = ci + di, cj + dj
                if nj < 0 or nj >= h:
                    continue
                ni %= w
                fac = passable(ni, nj)
                if fac is None:
                    continue
                nlat, nlon = ctr(ni, nj)
                ng = gc + hav(clat, clon, nlat, nlon) / fac
                key = (ni, nj)
                if ng < g.get(key, 1e18) - 1e-9:
                    g[key] = ng
                    came[key] = cur
                    heapq.heappush(heap, (ng + heur(ni, nj), ng, key))

    if goal not in came and goal != start:
        return None
    path = [goal]
    while path[-1] != start:
        path.append(came[path[-1]])
    path.reverse()
    return path


def _coarse_near_shore(i, j, cm, reach):
    for r in range(1, reach + 1):
        for dj in range(-r, r + 1):
            nj = j + dj
            if nj < 0 or nj >= CH:
                continue
            span = range(-r, r + 1) if abs(dj) == r else (-r, r)
            for di in span:
                if cm[nj * CW + ((i + di) % CW)]:
                    return True
    return False


def _coarse_field(a, b, water_factor, reach=None):
    """A lower bound on the cost from every coarse cell to the goal.

    Dijkstra outward from the goal over the 0.5-degree grid, where a cell counts
    as land if any fine cell in it is land. That optimism is the point: the field
    can only ever under-estimate the real cost, which is what an A* heuristic
    must do. Given it, the fine search walks almost straight to the goal instead
    of fanning out across a continent — and a destination the field never reaches
    is one there is no way to at all.

    The search is held to an ellipse around the two ends, so a walk across France
    doesn't cost a sweep of Asia. Cells outside it simply fall back to the
    great-circle bound.
    """
    cm = coarse()
    clat_res, clon_res = 180.0 / CH, 360.0 / CW

    def ctr(i, j):
        return 90 - (j + 0.5) * clat_res, -180 + ((i % CW) + 0.5) * clon_res

    def cell(lat, lon):
        return int((lon + 180) / clon_res) % CW, min(CH-1, max(0, int((90 - lat) / clat_res)))

    def land(i, j):
        return cm[j * CW + (i % CW)] == 1

    def snap_c(i, j):
        if water_factor is not None or land(i, j):
            return i, j
        for r in range(1, 8):
            for di in range(-r, r+1):
                for dj in range(-r, r+1):
                    if max(abs(di), abs(dj)) != r:
                        continue
                    ni, nj = (i + di) % CW, j + dj
                    if 0 <= nj < CH and land(ni, nj):
                        return ni, nj
        return i, j

    si, sj = snap_c(*cell(*a))
    gi, gj = snap_c(*cell(*b))
    crow = hav(a[0], a[1], b[0], b[1])
    budget = 1.5 * crow + 600.0

    def inside(i, j):
        la, lo = ctr(i, j)
        return hav(la, lo, a[0], a[1]) + hav(la, lo, b[0], b[1]) <= budget

    dist = {(gi, gj): 0.0}
    heap = [(0.0, (gi, gj))]
    done = set()
    while heap:
        d, cur = heapq.heappop(heap)
        if cur in done:
            continue
        done.add(cur)
        ci, cj = cur
        cla, clo = ctr(ci, cj)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di == 0 and dj == 0:
                    continue
                ni, nj = ci + di, cj + dj
                if nj < 0 or nj >= CH:
                    continue
                ni %= CW
                if land(ni, nj):
                    fac = BEST_FACTOR
                elif water_factor is None:
                    continue
                elif reach is not None and not _coarse_near_shore(ni, nj, cm, reach):
                    continue
                else:
                    fac = water_factor
                if not inside(ni, nj):
                    continue
                nla, nlo = ctr(ni, nj)
                nd = d + hav(cla, clo, nla, nlo) / fac
                if nd < dist.get((ni, nj), 1e18) - 1e-9:
                    dist[(ni, nj)] = nd
                    heapq.heappush(heap, (nd, (ni, nj)))
    return dist, (si, sj)


def _find(a, b, boat="none", cost_at=None, max_cells=1400000):
    """a, b are (lat, lon). Returns (waypoints, ok, water_fraction).

    waypoints includes both ends. ok is False when no route exists at all,
    in which case the straight line is handed back so the caller can still
    say something.
    """
    bo = BOATS[boat]
    water_factor = bo["water"]

    ai, aj = snap(*cell_of(*a), allow_water=water_factor is not None)
    bi, bj = snap(*cell_of(*b), allow_water=water_factor is not None)
    if (ai, aj) == (bi, bj):
        return [a, b], True, 0.0

    if water_factor is None:
        # a party that will not get its feet wet cannot leave its own landmass,
        # and knowing that costs two lookups instead of a search of half Europe
        ca = COMP_GRID[aj * MW + ai]
        cb = COMP_GRID[bj * MW + bi]
        if ca and cb and ca != cb and 255 not in (ca, cb):
            return [a, b], False, 0.0

    field, _cstart = _coarse_field(a, b, water_factor,
                                   None if bo.get("reach") is None else
                                   max(1, bo["reach"] // CF + 1))
    if (ai // CF, aj // CF) not in field:
        # the coarse grid, which forgives every strait it can, cannot get there
        return [a, b], False, 0.0

    glat, glon = centre(bi, bj)
    slack = 90.0        # a coarse cell is half a degree; don't over-claim

    def heur(i, j):
        la, lo = centre(i, j)
        gc = hav(la, lo, glat, glon) / BEST_FACTOR
        c = field.get((i // CF, j // CF))
        return gc if c is None else max(gc, c - slack)

    reach = bo.get("reach")

    def passable(i, j):
        if LAND[j * MW + (i % MW)]:
            if cost_at is None:
                return 1.0
            return max(0.15, cost_at(*centre(i, j)))
        if water_factor is None:
            return None
        if reach is not None and not near_shore(i, j, reach):
            return None
        return water_factor

    path = _astar((ai, aj), (bi, bj), MW, MH, passable, heur, max_cells)
    if path is None:
        return [a, b], False, 0.0

    pts = [a] + [centre(i, j) for i, j in path[1:-1]] + [b]
    wet = sum(1 for i, j in path if not LAND[j * MW + (i % MW)])
    return simplify(pts, 12.0), True, wet / max(1, len(path))


def snap(i, j, allow_water=False, radius=10):
    """Nudge an endpoint onto land, so a quayside town isn't stranded at sea."""
    if allow_water or is_land_cell(i, j):
        return i, j
    for r in range(1, radius+1):
        best, bd = None, 1e9
        for di in range(-r, r+1):
            for dj in range(-r, r+1):
                if max(abs(di), abs(dj)) != r:
                    continue
                ni, nj = (i+di) % MW, j+dj
                if 0 <= nj < MH and is_land_cell(ni, nj):
                    d = di*di + dj*dj
                    if d < bd:
                        best, bd = (ni, nj), d
        if best:
            return best
    return i, j


def simplify(pts, tol_km):
    """Douglas-Peucker, so a grid path becomes a handful of waypoints."""
    if len(pts) < 3:
        return pts
    def rdp(lo, hi):
        if hi <= lo + 1:
            return []
        a, b = pts[lo], pts[hi]
        worst, wi = -1.0, -1
        for k in range(lo+1, hi):
            d = seg_dist(pts[k], a, b)
            if d > worst:
                worst, wi = d, k
        if worst <= tol_km:
            return []
        return rdp(lo, wi) + [wi] + rdp(wi, hi)
    keep = [0] + rdp(0, len(pts)-1) + [len(pts)-1]
    return [pts[k] for k in keep]


def seg_dist(p, a, b):
    """Rough cross-track distance in km, good enough for simplifying."""
    kx = math.cos(math.radians(p[0])) * 111.32
    ky = 110.57
    px_, py_ = (p[1]-a[1])*kx, (p[0]-a[0])*ky
    bx, by = (b[1]-a[1])*kx, (b[0]-a[0])*ky
    L = bx*bx + by*by
    t = 0.0 if L == 0 else max(0.0, min(1.0, (px_*bx + py_*by)/L))
    dx, dy = px_ - t*bx, py_ - t*by
    return math.hypot(dx, dy)
