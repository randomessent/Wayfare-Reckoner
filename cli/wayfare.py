#!/usr/bin/env python3
"""Wayfare - pre-modern overland travel-time estimator for Europe.

Estimates how long a person or party takes to travel between two modern
European cities in a world stripped of modern infrastructure: a handful of
the old paved roads, cart tracks, and a great deal of wilderness.

Usage:
    python3 wayfare.py --from Lyon --to Zagreb --mode horse --rest medium
    python3 wayfare.py --from Lisbon --to Toledo --mode foot --rest low \
        --weather heavy_rain --season autumn --depart 04:00 --party 6 --json
"""
from __future__ import annotations
import argparse, json, math, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# The world has to be chosen before the gazetteer is imported, because the
# gazetteer reads its files at import. --world on the command line wins over
# WAYFARE_WORLD in the environment; both default to our own earth.
for _i, _a in enumerate(sys.argv):
    if _a == "--world" and _i + 1 < len(sys.argv):
        os.environ["WAYFARE_WORLD"] = sys.argv[_i + 1]
    elif _a.startswith("--world="):
        os.environ["WAYFARE_WORLD"] = _a.split("=", 1)[1]
_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
WORLDS = ["earth"] + sorted(d for d in os.listdir(_DATA)
                            if os.path.isfile(os.path.join(_DATA, d, "grids.json")))

from gazetteer import (PLACES, resolve, resolve_city, zone_at,  # noqa: E402
                       PlaceNotFound, suggest, landmass)
from gazetteer import nearest_place as gz_nearest  # noqa: E402
import router  # noqa: E402
from router import BOATS  # noqa: E402

R_EARTH = 6371.0

# --------------------------------------------------------------------------
# Terrain
# --------------------------------------------------------------------------
# sinuosity : how much longer the walkable path is than the crow-flight line
#             (detours around ridges, bogs, gorges, fording points)
# speed     : multiplier on the party's base pace
# exposure  : how hard weather bites here (1.0 = average)
TERRAIN = {
    "plain":          dict(label="open plain",        sinuosity=1.14, speed=1.00, exposure=1.10),
    "farmland":       dict(label="settled farmland",  sinuosity=1.16, speed=1.00, exposure=1.15),
    "river_plain":    dict(label="river plain",       sinuosity=1.13, speed=1.02, exposure=1.20),
    "river_valley":   dict(label="river valley road", sinuosity=1.12, speed=1.03, exposure=0.95),
    "steppe_plain":   dict(label="grass steppe",      sinuosity=1.12, speed=1.00, exposure=1.15),
    "steppe_plateau": dict(label="arid plateau",      sinuosity=1.16, speed=0.95, exposure=1.05),
    "coastal":        dict(label="coastal lowland",   sinuosity=1.22, speed=0.94, exposure=1.05),
    "coastal_karst":  dict(label="karst coast",       sinuosity=1.38, speed=0.72, exposure=1.10),
    "hills":          dict(label="rolling hills",     sinuosity=1.24, speed=0.88, exposure=1.00),
    "upland":         dict(label="high moorland",     sinuosity=1.32, speed=0.80, exposure=1.25),
    "forest_plain":   dict(label="lowland forest",    sinuosity=1.24, speed=0.86, exposure=0.85),
    "forest_hills":   dict(label="wooded hills",      sinuosity=1.32, speed=0.78, exposure=0.90),
    "forest_upland":  dict(label="forested uplands",  sinuosity=1.38, speed=0.72, exposure=0.95),
    "marsh_plain":    dict(label="marsh and delta",   sinuosity=1.34, speed=0.72, exposure=1.45),
    "mountain":       dict(label="mountains",         sinuosity=1.55, speed=0.63, exposure=1.30),
    "high_mountain":  dict(label="high mountains",    sinuosity=1.62, speed=0.55, exposure=1.55),
    "savanna":        dict(label="savanna",           sinuosity=1.14, speed=0.98, exposure=1.20),
    "desert":         dict(label="desert",            sinuosity=1.12, speed=0.90, exposure=1.45),
    "sand_sea":       dict(label="sand sea",          sinuosity=1.30, speed=0.62, exposure=1.60),
    "rainforest":     dict(label="rainforest",        sinuosity=1.45, speed=0.52, exposure=0.90),
    "taiga":          dict(label="boreal forest",     sinuosity=1.35, speed=0.70, exposure=1.15),
    "tundra":         dict(label="tundra",            sinuosity=1.25, speed=0.78, exposure=1.50),
    "high_plateau":   dict(label="high plateau",      sinuosity=1.40, speed=0.58, exposure=1.50),
    "open_water":     dict(label="open water",        sinuosity=1.02, speed=1.00, exposure=1.30),
}

# --------------------------------------------------------------------------
# Modes of travel. Base pace is km/h of ACTUAL MOVEMENT on decent going.
# --------------------------------------------------------------------------
MODES = {
    "foot": dict(
        label="on foot", pace=4.3, sustainable_hours=8.0, max_hours=15.0, hard_days=8,
        note="Unburdened adult walking pace; a laden traveller sits nearer 4 km/h."),
    "foot_laden": dict(
        label="on foot with baggage", pace=3.6, sustainable_hours=7.5, max_hours=13.0, hard_days=7,
        note="Packs, a handcart, or driven animals."),
    "horse": dict(
        label="on horseback", pace=8.0, sustainable_hours=9.0, max_hours=16.0, hard_days=6,
        note="Endurance-bred mount alternating walk and trot, rider dismounting on climbs."),
    "horse_remount": dict(
        label="on horseback with remounts", pace=9.8, sustainable_hours=10.0, max_hours=18.0, hard_days=9,
        note="A led spare horse per rider, swapped every few hours."),
    "cart": dict(
        label="with carts", pace=3.2, sustainable_hours=8.0, max_hours=12.0, hard_days=8,
        note="Wheeled transport; confined to roads and tracks, and hostage to mud."),
}

# --------------------------------------------------------------------------
# Rest regimes
# --------------------------------------------------------------------------
REGIMES = {
    "high": dict(
        label="Unhurried", hours=6.0, wander=1.06, night_ok=False, fatigue_rate=0.006,
        note="Full night's sleep, a proper camp, meals, and time to look around."),
    "medium": dict(
        label="Purposeful", hours=8.0, wander=1.00, night_ok=False, fatigue_rate=0.006,
        note="Seven hours' sleep, quick camp, halts only to water animals and eat cold."),
    "low": dict(
        label="Driven", hours=13.0, wander=0.98, night_ok=True, fatigue_rate=0.006,
        note="Four to five hours' snatched sleep, night marching, no halt that isn't forced."),
}

# --------------------------------------------------------------------------
# Roads, weather, season
# --------------------------------------------------------------------------
ROADS = {
    "roads":      dict(label="the old paved roads", sinuosity=0.90, speed=1.10),
    "mixed":      dict(label="main roads and cart trails", sinuosity=1.00, speed=1.00),
    "trails":     dict(label="cart trails and drove roads", sinuosity=1.08, speed=0.90),
    "wilderness": dict(label="pathless country", sinuosity=1.24, speed=0.70),
}

WEATHER = {
    "clear":      dict(label="clear",             speed=1.00, halt=0.00),
    "overcast":   dict(label="grey and dry",      speed=0.99, halt=0.00),
    "wind":       dict(label="hard wind",         speed=0.94, halt=0.00),
    "fog":        dict(label="fog",               speed=0.80, halt=0.02),
    "light_rain": dict(label="intermittent rain", speed=0.93, halt=0.00),
    "heavy_rain": dict(label="heavy rain",        speed=0.74, halt=0.04),
    "storm":      dict(label="storms",            speed=0.55, halt=0.14),
    "heat":       dict(label="punishing heat",    speed=0.85, halt=0.03),
    "snow":       dict(label="snow",              speed=0.58, halt=0.08),
    "deep_snow":  dict(label="deep snow",         speed=0.34, halt=0.20),
}

SEASONS = {
    "spring": dict(declination=  4.0, label="spring"),
    "summer": dict(declination= 21.0, label="summer"),
    "autumn": dict(declination= -4.0, label="autumn"),
    "winter": dict(declination=-21.0, label="winter"),
}

MOUNTS = {
    # Each tier has a horse everyone already knows, because "1.10x speed and an
    # extra hour in the saddle" means nothing to a reader and Bucephalus does.
    "mundane":     dict(label="ordinary stock",      speed=0.94, hours=-1.0,
                        like="a Rocinante", lore="Don Quixote's bony nag: willing enough, and no more than that"),
    "hardy":       dict(label="endurance-bred",      speed=1.00, hours=0.0,
                        like="a Marengo", lore="Napoleon's grey Arabian, who carried him at Austerlitz and out of Russia"),
    "exceptional": dict(label="exceptional bloodstock", speed=1.10, hours=1.0,
                        like="a Bucephalus", lore="Alexander's, whom no one else could ride, and who went as far as the Hydaspes"),
    "otherworldly":dict(label="otherworldly",        speed=1.30, hours=3.0,
                        like="a Shadowfax", lore="lord of horses, who bore no saddle and outran the wind"),
}

# --------------------------------------------------------------------------
# Register — how much fantasy is allowed into the reckoning.
# Scale is separate and answers "is this our map, or a bigger world?".
# --------------------------------------------------------------------------
REGISTERS = {
    "chronicle": dict(
        label="Chronicle", wilderness=1.00, endurance=0.0, fatigue=1.00,
        hazard_floor="none", mounts=("mundane", "hardy"),
        note="The land is as it is mapped and people tire on schedule. "
             "Nothing here that a 12th-century itinerary could not vouch for."),
    "romance": dict(
        label="Romance", wilderness=1.06, endurance=0.5, fatigue=0.85,
        hazard_floor="low", mounts=("mundane", "hardy", "exceptional"),
        note="The wilds are deeper than the map admits and the roads less certain, "
             "but the people who cross them are built to."),
    "saga": dict(
        label="Saga", wilderness=1.14, endurance=1.5, fatigue=0.65,
        hazard_floor="moderate", mounts=("mundane", "hardy", "exceptional", "otherworldly"),
        note="The map is a rumour. Forests run for weeks and the roads are older than "
             "anyone living — and the people in this story do not tire like farmhands."),
}

HAZARD = {
    "none":     dict(label="none",     rate=0.000),
    "low":      dict(label="low",      rate=0.020),
    "moderate": dict(label="moderate", rate=0.055),
    "high":     dict(label="high",     rate=0.110),
}

NIGHT_SPEED = 0.55


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------
def haversine(a_lat, a_lon, b_lat, b_lon):
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp = p2 - p1
    dl = math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_EARTH * math.asin(math.sqrt(h))


def interpolate(a_lat, a_lon, b_lat, b_lon, f):
    """Great-circle interpolation, fraction f from A to B."""
    d = haversine(a_lat, a_lon, b_lat, b_lon) / R_EARTH
    if d < 1e-9:
        return a_lat, a_lon
    p1, l1 = math.radians(a_lat), math.radians(a_lon)
    p2, l2 = math.radians(b_lat), math.radians(b_lon)
    A = math.sin((1 - f) * d) / math.sin(d)
    B = math.sin(f * d) / math.sin(d)
    x = A * math.cos(p1) * math.cos(l1) + B * math.cos(p2) * math.cos(l2)
    y = A * math.cos(p1) * math.sin(l1) + B * math.cos(p2) * math.sin(l2)
    z = A * math.sin(p1) + B * math.sin(p2)
    return math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x))


def daylight_hours(lat, declination):
    p, d = math.radians(lat), math.radians(declination)
    c = -math.tan(p) * math.tan(d)
    if c <= -1: return 24.0
    if c >= 1:  return 0.0
    return 2 * math.degrees(math.acos(c)) / 15.0


def nearest_place(lat, lon):
    """The nearest place worth naming. A camp is described by the town it is
    near, and with 171,000 of them a hamlet of 900 is not a landmark — so ask
    for somewhere of a few thousand souls first, and settle for less only if
    the country is empty."""
    for floor in (20000, 2000, 0):
        name, d = gz_nearest(lat, lon, floor)
        if name and d < (140 if floor else 400):
            return name, d
    return None, 1e9


def party_factor(n):
    if n <= 3:   return 1.00, "a handful of travellers"
    if n <= 10:  return 0.97, "a small band"
    if n <= 30:  return 0.92, "a large company"
    if n <= 100: return 0.85, "a small column"
    return 0.78, "a host"


# --------------------------------------------------------------------------
# Route construction
# --------------------------------------------------------------------------
def terrain_speed(lat, lon):
    """What the router uses to prefer easy ground over hard."""
    return TERRAIN[zone_at(lat, lon)[1]]["speed"]


def build_route(points, road_key, regime_key, mode_key, season_key, weather_key,
                register_key="chronicle", scale=1.0, boat="none"):
    """points: list of place names, origin first, destination last."""
    hits = [resolve(p) for p in points]
    nodes = [(h["name"], h["lat"], h["lon"], h["elev"]) for h in hits]
    legs = list(zip(nodes[:-1], nodes[1:]))
    gc = sum(haversine(x[1], x[2], y[1], y[2]) for x, y in legs)

    # find a way across the ground first — the old model drew a straight line
    # and asked what was under it, which is fine until the line crosses a sea
    segs, blocked = [], False
    for x, y in legs:
        way, ok, _wet = router.find((x[1], x[2]), (y[1], y[2]), boat,
                                    cost_at=terrain_speed)
        if not ok:
            blocked = True
        allow_water = boat != "none" or not ok
        for k in range(len(way) - 1):
            a = ("", way[k][0], way[k][1], 0)
            b = ("", way[k+1][0], way[k+1][1], 0)
            segs.extend(_leg_segments(a, b, road_key, regime_key, mode_key,
                                      season_key, weather_key, register_key, scale,
                                      allow_water))
    return nodes[0], nodes[-1], gc * scale, segs, hits, blocked


def _leg_segments(a, b, road_key, regime_key, mode_key, season_key, weather_key,
                  register_key="chronicle", scale=1.0, allow_water=False):
    gc = haversine(a[1], a[2], b[1], b[2])
    n = max(10, int(gc / 15))
    road = ROADS[road_key]
    wander = REGIMES[regime_key]["wander"] * REGISTERS[register_key]["wilderness"]
    wx = WEATHER[weather_key]
    winter = season_key == "winter"
    cart = mode_key == "cart"

    segs = []
    for i in range(n):
        f0, f1 = i / n, (i + 1) / n
        p0 = interpolate(a[1], a[2], b[1], b[2], f0)
        p1 = interpolate(a[1], a[2], b[1], b[2], f1)
        mid = interpolate(a[1], a[2], b[1], b[2], (f0 + f1) / 2)
        # the router already proved a way over land, so water under a chord
        # here is the chart cutting a corner off a bay, not a real crossing
        wet = allow_water and not router.is_land_cell(*router.cell_of(*mid))
        if wet:
            zone_label, tkey = "Open Water", "open_water"
        else:
            zone_label, tkey = zone_at(*mid)
        t = TERRAIN[tkey]

        sin_f = t["sinuosity"] * road["sinuosity"] * wander
        spd_f = t["speed"] * road["speed"]

        notes = []
        if cart and tkey in ("mountain", "high_mountain", "marsh_plain", "coastal_karst", "forest_upland"):
            sin_f *= 1.30; spd_f *= 0.70
            notes.append("carts must go the long way round")
        if winter and tkey == "high_mountain":
            sin_f *= 1.15; spd_f *= 0.68
            notes.append("passes choked or closed")
        elif winter and tkey == "mountain":
            spd_f *= 0.78
            notes.append("snow on the heights")

        # weather bites harder on exposed or boggy ground
        shortfall = (1.0 - wx["speed"]) * t["exposure"]
        spd_f *= max(0.30, 1.0 - shortfall)
        spd_f = max(0.20, spd_f)   # nothing crawls slower than a fifth of base pace

        gc_len = haversine(p0[0], p0[1], p1[0], p1[1])
        if wet:
            sin_f, spd_f = 1.02, 1.0
        segs.append(dict(
            zone=zone_label, terrain=tkey, terrain_label=t["label"], water=wet,
            gc_km=gc_len * scale, km=gc_len * sin_f * scale, speed_factor=spd_f,
            lat0=p0[0], lon0=p0[1], lat1=p1[0], lon1=p1[1], notes=notes))

    return segs


# --------------------------------------------------------------------------
# Journey simulation
# --------------------------------------------------------------------------
def simulate(segs, mode_key, regime_key, depart_hour, mean_lat, season_key,
             party, mount_key, weather_key, night_travel=None, register_key="chronicle",
             boat="none"):
    mode, regime = MODES[mode_key], REGIMES[regime_key]
    reg = REGISTERS[register_key]
    mounted = mode_key.startswith("horse")
    mount = MOUNTS[mount_key]

    pfac, plabel = party_factor(party)
    pace = mode["pace"] * pfac * (mount["speed"] if mounted else 1.0)
    sustainable = mode["sustainable_hours"] + (mount["hours"] if mounted else 0.0) \
        + reg["endurance"]
    budget = min(regime["hours"], mode["max_hours"])
    night_ok = regime["night_ok"] if night_travel is None else night_travel

    dl = daylight_hours(mean_lat, SEASONS[season_key]["declination"])
    sunrise, sunset = 12 - dl / 2, 12 + dl / 2
    halt_rate = WEATHER[weather_key]["halt"]

    sea_pace = BOATS[boat].get("sea_pace", 5.0)
    sea_hours_today = 0.0
    sea_km = 0.0
    total_km = sum(s["km"] for s in segs)
    t = float(depart_hour)          # clock hours since midnight of departure day
    start_t = t
    done = 0.0                      # km travelled
    si = 0                          # current segment
    seg_done = 0.0
    fatigue = 0.0
    strain = 0            # consecutive days pushed past what the party can sustain
    hard_days = mode["hard_days"] + (2 if register_key == "saga" else
                                     1 if register_key == "romance" else 0)
    hours_today = 0.0
    night_hours = 0.0
    day_index = int(t // 24)
    day_km = 0.0
    day_zones = []
    days = []
    rest_days = 0
    weather_halt_days = 0.0
    guard = 0

    def close_day(kind="march"):
        nonlocal day_km, day_zones, hours_today
        lat, lon = position(segs, done)
        place, pd = nearest_place(lat, lon)
        days.append(dict(
            day=len(days) + 1, kind=kind, km=round(day_km, 1),
            hours=round(hours_today, 1),
            zones=list(dict.fromkeys(day_zones)),
            camp=place, camp_km=round(pd),
            fatigue=round(fatigue, 3),
            cumulative_km=round(done, 1)))
        day_km, day_zones, hours_today = 0.0, [], 0.0

    while done < total_km - 1e-6 and guard < 400000:
        guard += 1
        tod = t % 24
        is_night = tod < sunrise - 1e-6 or tod >= sunset

        # Waiting out the dark before the first step of a day costs no day.
        if hours_today == 0.0 and is_night and not (night_ok or segs[si].get("water", False)):
            nxt = (t - tod) + (sunrise if tod < sunrise else 24 + sunrise)
            t = nxt if nxt > t + 1e-6 else nxt + 24
            continue

        at_sea = segs[si].get("water", False)
        budget_now = 20.0 if at_sea else budget
        night_now = night_ok or at_sea
        if hours_today >= budget_now - 1e-9 or (is_night and not night_now):
            # a day mostly spent aboard costs the party nothing in legs
            over = 0.0 if sea_hours_today > hours_today/2 else max(0.0, hours_today - sustainable)
            fatigue += over * regime["fatigue_rate"] * reg["fatigue"]
            # a night's sleep: a fixed amount back, plus a share of what's there,
            # so tiredness settles at a plateau rather than compounding to a halt
            fatigue = max(0.0, min(0.30, fatigue - 0.010 - 0.15 * fatigue))
            strain = strain + 1 if over > 0.25 else 0
            sea_hours_today = 0.0
            close_day()
            # they can only push past their limit for so many days running
            if strain >= hard_days:
                lat, lon = position(segs, done)
                place, pd = nearest_place(lat, lon)
                days.append(dict(day=len(days) + 1, kind="rest", km=0.0, hours=0.0,
                                 zones=[], camp=place, camp_km=round(pd),
                                 fatigue=round(fatigue, 3), cumulative_km=round(done, 1),
                                 note="forced halt — the animals or the people are spent"
                                 if mounted else "forced halt — the party is spent"))
                fatigue *= 0.30
                strain = 0
                rest_days += 1
                t += 24
            t = (t - (t % 24)) + 24 + sunrise + 1e-6
            continue

        seg = segs[si]
        if seg.get("water"):
            speed = sea_pace
        else:
            speed = pace * seg["speed_factor"] * (1.0 - fatigue)
            if is_night:
                speed *= NIGHT_SPEED
        speed = max(0.35, speed)

        dt = min(0.25, budget_now - hours_today)
        if dt <= 1e-9:
            continue
        step = speed * dt
        remaining_seg = seg["km"] - seg_done
        if step >= remaining_seg:
            step = remaining_seg
            dt = step / speed if speed else 0.0
            seg_done = 0.0
            day_zones.append(seg["zone"])
            si += 1
            if si >= len(segs):
                si = len(segs) - 1
                done = total_km
                hours_today += dt; t += dt
                if is_night: night_hours += dt
                day_km += step
                break
        else:
            seg_done += step
            day_zones.append(seg["zone"])

        done += step
        day_km += step
        hours_today += dt
        if seg.get("water"):
            sea_hours_today += dt
            sea_km += step
        if is_night:
            night_hours += dt
        t += dt

    if day_km > 0 or hours_today > 0:
        close_day()

    elapsed = t - start_t
    # weather can simply stop a party outright on some days
    halt_days = round(len([d for d in days if d["kind"] == "march"]) * halt_rate, 2)

    return dict(
        elapsed_hours=elapsed, sea_km=sea_km,
        travel_days=len([d for d in days if d["kind"] == "march"]),
        rest_days=rest_days,
        weather_halt_days=halt_days,
        night_hours=round(night_hours, 1),
        days=days,
        pace=pace,
        budget=budget,
        sustainable=sustainable,
        end_fatigue=fatigue,
        daylight=dl, sunrise=sunrise, sunset=sunset,
        party_label=plabel,
        total_km=total_km)


def position(segs, km):
    acc = 0.0
    for s in segs:
        if acc + s["km"] >= km:
            f = (km - acc) / s["km"] if s["km"] else 0.0
            return interpolate(s["lat0"], s["lon0"], s["lat1"], s["lon1"], f)
        acc += s["km"]
    last = segs[-1]
    return last["lat1"], last["lon1"]


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------
def dh(hours):
    d = int(hours // 24)
    h = hours - d * 24
    return d, h


def fmt_dh(hours):
    d, h = dh(hours)
    if d and h >= 0.05:
        return f"{d} day{'s' if d != 1 else ''}, {h:.1f} hours"
    if d:
        return f"{d} day{'s' if d != 1 else ''}"
    return f"{h:.1f} hours"


def run(args):
    reg = REGISTERS[args.register]

    # the register decides which mounts are even in the story, and sets a
    # floor under how much can go wrong
    mount = args.mount if args.mount in reg["mounts"] else reg["mounts"][-1]
    order = list(HAZARD)
    hazard_key = args.hazard
    if order.index(hazard_key) < order.index(reg["hazard_floor"]):
        hazard_key = reg["hazard_floor"]

    points = [args.origin] + list(args.via or []) + [args.dest]
    a, b, gc, segs, hits, blocked = build_route(
        points, args.roads, args.rest, args.mode, args.season, args.weather,
        args.register, args.scale, args.boat)
    mean_lat = (a[1] + b[1]) / 2
    sim = simulate(segs, args.mode, args.rest, args.depart_hour, mean_lat,
                   args.season, args.party, mount, args.weather, args.night,
                   args.register, args.boat)
    embarkations = sum(1 for i in range(1, len(segs))
                       if segs[i].get("water") and not segs[i-1].get("water"))
    if segs and segs[0].get("water"):
        embarkations += 1
    embark_hours = embarkations * BOATS[args.boat].get("embark", 0.0)

    haz = HAZARD[hazard_key]
    hazard_days = sim["travel_days"] * haz["rate"]
    extra = sim["weather_halt_days"] + hazard_days
    sim["elapsed_hours"] += embark_hours
    likely_low = sim["elapsed_hours"]
    likely_high = sim["elapsed_hours"] + extra * 24 * 2.0
    expected = sim["elapsed_hours"] + extra * 24

    zones = {}
    for s in segs:
        zones.setdefault(s["zone"], 0.0)
        zones[s["zone"]] += s["km"]

    result = dict(
        origin=a[0], destination=b[0],
        via=[h["name"] for h in hits[1:-1]],
        origin_region=hits[0]["region"], destination_region=hits[-1]["region"],
        places=[dict(name=h["name"], region=h["region"], kind=h["kind"],
                     lat=round(h["lat"], 4), lon=round(h["lon"], 4),
                     matched_as=h["matched_as"]) for h in hits],
        straight_line_km=round(gc, 1),
        travelled_km=round(sim["total_km"], 1),
        detour_ratio=round(sim["total_km"] / gc, 2),
        mode=MODES[args.mode]["label"], rest=REGIMES[args.rest]["label"],
        roads=ROADS[args.roads]["label"], weather=WEATHER[args.weather]["label"],
        season=args.season, party=args.party, party_label=sim["party_label"],
        depart=f"{int(args.depart_hour):02d}:{int(round((args.depart_hour%1)*60)):02d}",
        daylight_hours=round(sim["daylight"], 1),
        effective_pace_kmh=round(sim["pace"], 2),
        hours_on_the_move_per_day=sim["budget"],
        best_case=dict(days=dh(likely_low)[0], hours=round(dh(likely_low)[1], 1),
                       total_hours=round(likely_low, 1), text=fmt_dh(likely_low)),
        expected=dict(days=dh(expected)[0], hours=round(dh(expected)[1], 1),
                      total_hours=round(expected, 1), text=fmt_dh(expected)),
        worst_case=dict(days=dh(likely_high)[0], hours=round(dh(likely_high)[1], 1),
                        total_hours=round(likely_high, 1), text=fmt_dh(likely_high)),
        arrival_day=int((args.depart_hour + expected) // 24) + 1,
        arrival_clock="{:02d}:{:02d}".format(
            int((args.depart_hour + expected) % 24),
            int(round((((args.depart_hour + expected) % 24) % 1) * 60)) % 60),
        travel_days=sim["travel_days"], forced_rest_days=sim["rest_days"],
        weather_halt_days=sim["weather_halt_days"],
        hazard_delay_days=round(hazard_days, 2), hazard=haz["label"],
        register=reg["label"], register_note=reg["note"], world_scale=args.scale,
        mount=MOUNTS[mount]["label"], mount_like=MOUNTS[mount]["like"],
        mount_forced=(mount != args.mount), hazard_forced=(hazard_key != args.hazard),
        night_hours=sim["night_hours"],
        boat=BOATS[args.boat]["label"], boat_key=args.boat,
        sea_km=round(sim["sea_km"], 1), embarkations=embarkations,
        embark_hours=round(embark_hours, 1), route_blocked=blocked,
        terrain_share=[dict(zone=k, km=round(v, 1), pct=round(100 * v / sim["total_km"]))
                       for k, v in sorted(zones.items(), key=lambda x: -x[1])],
        itinerary=sim["days"],
    )
    return result


def render(r):
    L = []
    路 = "  →  ".join([r['origin']] + r.get('via', []) + [r['destination']])
    L.append(f"  {路}")
    for pl in r["places"]:
        tag = "" if pl["matched_as"] == "name" else f"  [{pl['matched_as']}]"
        L.append(f"    {pl['name']} — {pl['region']}{tag}")
    L.append("  " + "─" * 58)
    L.append(f"  {r['expected']['text'].upper()}")
    L.append(f"  (best case {r['best_case']['text']} · bad luck {r['worst_case']['text']})")
    L.append(f"  leaving at {r['depart']}, they arrive on day {r['arrival_day']} "
             f"around {r['arrival_clock']}")
    L.append("")
    L.append(f"  {r['straight_line_km']:.0f} km as the crow flies · "
             f"{r['travelled_km']:.0f} km actually walked (×{r['detour_ratio']})")
    L.append(f"  {r['party']} travelling {r['mode']} — {r['party_label']}")
    L.append(f"  {r['rest'].lower()} pace · {r['hours_on_the_move_per_day']} h on the move per day "
             f"· {r['effective_pace_kmh']} km/h moving")
    scale_txt = "our own map" if abs(r['world_scale'] - 1.0) < 1e-6 else \
        f"a world ×{r['world_scale']:g} the size of ours"
    mount_txt = f"{r['mount']} mounts"
    if r["mode"].startswith("on horseback"):
        mount_txt += f" — {r['mount_like']}"
    L.append(f"  {r['register']} register · {scale_txt} · {mount_txt}")
    if r["route_blocked"]:
        L.append("  ⚠ NO WAY ROUND — open water lies across this journey and the party")
        L.append("    has no boat. The figures below are for the straight line only.")
    elif r["sea_km"]:
        L.append(f"  by {r['boat']} · {r['sea_km']:.0f} km of it on the water"
                 f" · {r['embarkations']} embarkation{'s' if r['embarkations'] != 1 else ''}"
                 f" (+{r['embark_hours']:.0f} h waiting for boats)")
    L.append(f"  {r['roads']} · {r['weather']} · {r['season']} "
             f"({r['daylight_hours']} h daylight) · departing {r['depart']}")
    L.append("")
    L.append(f"  {r['travel_days']} marching days"
             + (f" · {r['forced_rest_days']} forced rest days" if r['forced_rest_days'] else "")
             + (f" · {r['night_hours']} h travelled in darkness" if r['night_hours'] else ""))
    if r['weather_halt_days']:
        L.append(f"  weather is expected to pin them down ~{r['weather_halt_days']} days")
    if r['hazard_delay_days']:
        L.append(f"  {r['hazard']} hazard adds ~{r['hazard_delay_days']} days of delay")
    L.append("")
    forced = []
    if r.get('mount_forced'): forced.append("mounts held to what the register allows")
    if r.get('hazard_forced'): forced.append(f"hazard raised to {r['hazard']} by the register")
    if forced:
        L.append("  " + " · ".join(forced))
        L.append("")
    L.append("  GROUND CROSSED")
    for z in r["terrain_share"]:
        bar = "█" * max(1, round(z["pct"] / 4))
        L.append(f"    {z['zone']:<26}{z['km']:>6.0f} km  {bar} {z['pct']}%")
    L.append("")
    L.append("  ITINERARY")
    for d in r["itinerary"]:
        if d["kind"] == "rest":
            L.append(f"    Day {d['day']:>2}   —      halt  ({d.get('note','rest')})")
            continue
        pct = round(100 * d['cumulative_km'] / r['travelled_km'])
        if d["camp_km"] <= 12:
            where = f"{d['camp']}"
        elif d["camp_km"] <= 45:
            where = f"near {d['camp']}"
        else:
            zone = d["zones"][-1] if d["zones"] else "open country"
            where = f"in the {zone}, {d['camp_km']} km from {d['camp']}"
        L.append(f"    Day {d['day']:>2}  {d['km']:>5.0f} km in {d['hours']:>4.1f} h  →  {where}  [{pct}%]")
        if d["zones"]:
            L.append(f"            through {', '.join(d['zones'])}")
    return "\n".join(L)


def main():
    p = argparse.ArgumentParser(description="Pre-modern overland travel times, on earth or in Middle-earth.")
    p.add_argument("--world", default=os.environ.get("WAYFARE_WORLD", "earth"), choices=WORLDS,
                   help="which world the places are in")
    p.add_argument("--from", dest="origin", required=True)
    p.add_argument("--to", dest="dest", required=True)
    p.add_argument("--mode", default="foot", choices=list(MODES))
    p.add_argument("--rest", default="medium", choices=list(REGIMES))
    p.add_argument("--weather", default="clear", choices=list(WEATHER))
    p.add_argument("--season", default="summer", choices=list(SEASONS))
    p.add_argument("--roads", default="mixed", choices=list(ROADS))
    p.add_argument("--mount", default="hardy", choices=list(MOUNTS))
    p.add_argument("--hazard", default="none", choices=list(HAZARD))
    p.add_argument("--register", default="chronicle", choices=list(REGISTERS),
                   help="how much fantasy the reckoning allows in")
    p.add_argument("--boat", default="none", choices=list(BOATS),
                   help="what water they can cross")
    p.add_argument("--scale", type=float, default=1.0,
                   help="world scale: 1.0 is our map, 1.5 is half again as big")
    p.add_argument("--party", type=int, default=1)
    p.add_argument("--via", nargs="*", default=[],
                   help="waypoints to route through, in order")
    p.add_argument("--depart", default="06:00", help="departure clock time, e.g. 04:30 or 21:00")
    p.add_argument("--night", dest="night", action="store_true", default=None,
                   help="force night travel on")
    p.add_argument("--no-night", dest="night", action="store_false",
                   help="force night travel off")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()

    hh, _, mm = a.depart.partition(":")
    a.depart_hour = int(hh) + (int(mm) / 60 if mm else 0)

    try:
        r = run(a)
    except PlaceNotFound as e:
        print(f"No place matching \"{e.query}\" in the gazetteer.", file=sys.stderr)
        if e.suggestions:
            print("  Did you mean: " + ", ".join(e.suggestions) + "?", file=sys.stderr)
        print("  The gazetteer holds "
              f"{len(PLACES)} towns, ranges, forests and passes. For anywhere "
              "else, give coordinates:\n"
              '    --from "40.66,-4.70"        or   --from "Gredos camp @ 40.25,-5.30"',
              file=sys.stderr)
        return 2
    print(json.dumps(r, indent=2) if a.json else render(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
