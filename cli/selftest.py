#!/usr/bin/env python3
"""Sanity checks for the Wayfare model.

Two kinds of test:
  * monotonicity — pushing harder must never arrive later, and the dials must
    move the answer in the direction they claim to.
  * benchmarks   — the historical rates the model was tuned against.

Run:  python3 selftest.py
"""
import itertools, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wayfare as W
from gazetteer import WORLD  # noqa: E402  (set by WAYFARE_WORLD; see wayfare.py --world)


class Args:
    def __init__(self, **kw):
        self.origin, self.dest = kw.pop("origin"), kw.pop("dest")
        self.via = kw.pop("via", [])
        d = dict(mode="foot", rest="medium", weather="clear", season="summer",
                 roads="mixed", mount="hardy", hazard="none", party=1,
                 depart_hour=6.0, night=None, register="chronicle", scale=1.0,
                 boat="none")
        d.update(kw)
        self.__dict__.update(d)


def hours(**kw):
    return W.run(Args(**kw))["expected"]["total_hours"]


ROUTES = [
    ("Sierra de Gredos", "42.9679314, 0.6918912"),   # the one that caught this
    ("Lyon", "Zagreb"), ("Paris", "Rome"), ("Lisbon", "Toledo"),
    ("Vienna", "Budapest"), ("Geneva", "Milan"), ("Zagreb", "Budapest"),
    ("Barcelona", "Bordeaux"), ("Hamburg", "Prague"), ("Seville", "Santiago de Compostela"),
    ("Samarkand", "Kashgar"), ("Cairo", "Timbuktu"), ("Delhi", "Kabul"),
] if WORLD == "earth" else [
    ("Hobbiton", "Rivendell"), ("Bree", "Minas Tirith"), ("Edoras", "Helm's Deep"),
    ("Minas Tirith", "Barad-dûr"), ("Mithlond", "Erebor"), ("Dol Amroth", "Umbar"),
    ("Esgaroth", "Rivendell"), ("Isengard", "Dol Guldur"),
]
MODES = ["foot", "foot_laden", "horse", "horse_remount", "cart"]

failures = []


def check(name, ok, detail=""):
    if not ok:
        failures.append(f"{name}: {detail}")


# ── 1. pushing harder must never arrive later ──────────────────────────────
for (a, b), mode in itertools.product(ROUTES, MODES):
    for season, weather in [("summer", "clear"), ("winter", "heavy_rain")]:
        hi, med, low = (hours(origin=a, dest=b, mode=mode, rest=r,
                              season=season, weather=weather)
                        for r in ("high", "medium", "low"))
        check("rest ordering",
              low <= med <= hi,
              f"{a}->{b} {mode} {season}/{weather}: "
              f"driven {low/24:.1f}d, purposeful {med/24:.1f}d, unhurried {hi/24:.1f}d")

# ── 2. every dial moves the answer the way it claims ───────────────────────
for a, b in ROUTES:
    base = dict(origin=a, dest=b, mode="horse")
    check("better roads are faster",
          hours(roads="roads", **base) <= hours(roads="mixed", **base) <=
          hours(roads="trails", **base) <= hours(roads="wilderness", **base), f"{a}->{b}")
    check("worse weather is slower",
          hours(weather="clear", **base) <= hours(weather="heavy_rain", **base) <=
          hours(weather="storm", **base), f"{a}->{b}")
    check("winter is not faster than summer",
          hours(season="summer", **base) <= hours(season="winter", **base), f"{a}->{b}")
    check("bigger parties are slower",
          hours(party=1, **base) <= hours(party=40, **base) <=
          hours(party=400, **base), f"{a}->{b}")
    check("better mounts are faster",
          hours(mount="exceptional", **base) <= hours(mount="hardy", **base) <=
          hours(mount="mundane", **base), f"{a}->{b}")
    check("a bigger world takes longer",
          hours(scale=1.0, **base) < hours(scale=1.5, **base) <
          hours(scale=2.0, **base), f"{a}->{b}")
    check("remounts beat a single horse",
          hours(origin=a, dest=b, mode="horse_remount") <=
          hours(origin=a, dest=b, mode="horse"), f"{a}->{b}")
    check("riding beats walking",
          hours(origin=a, dest=b, mode="horse") <=
          hours(origin=a, dest=b, mode="foot"), f"{a}->{b}")
    # compare arrival on the wall clock, not hours elapsed: a late start banks a
    # night the early start has to spend later, so elapsed alone is the wrong test
    check("leaving earlier never arrives later",
          5.0 + hours(depart_hour=5.0, **base) <= 17.0 + hours(depart_hour=17.0, **base),
          f"{a}->{b}")


def middle_earth_checks():
    """The same kinds of check, against the ground the ME-DEM team drew and
    the distances Tolkien wrote down."""
    from gazetteer import is_land, landmass, LATS, LONS, NAMES  # noqa: E402
    import router  # noqa: E402

    # Harbour towns and islands land wet at eleven kilometres; the tail should
    # still be short.
    wet = [NAMES[i] for i in range(len(NAMES)) if not is_land(LATS[i], LONS[i])]
    check("land mask", len(wet) <= len(NAMES) * 0.09,
          f"{len(wet)} of {len(NAMES)} places fall in the sea, e.g. {wet[:5]}")

    for label, (lo, la) in {"Belegaer off Lindon": (-13.1, 50.96), "the Bay of Belfalas": (5.75, 38.84),
                            "the Sea of Rhûn": (27.2, 48.77), "the Gulf of Lhûn": (-8.3, 51.41)}.items():
        check("land mask", not is_land(la, lo), f"{label} is drawn as land")
    for name in ("Hobbiton", "Bree", "Rivendell", "Edoras", "Minas Tirith", "Barad-dûr",
                 "Erebor", "Umbar", "Carn Dûm", "Isengard"):
        p = W.resolve(name)
        check("land mask", is_land(p["lat"], p["lon"]), f"{name} is drawn as sea")

    def at(name):
        p = W.resolve(name)
        return p["lat"], p["lon"]
    check("landmass", landmass(*at("Hobbiton")) == landmass(*at("Minas Tirith")),
          "the Shire and Gondor should be one landmass")
    check("landmass", landmass(*at("Bree")) == landmass(*at("Edoras")),
          "Bree and Edoras should be one landmass")
    check("landmass", landmass(*at("Hobbiton")) != landmass(*at("Himring")),
          "Himring is an island")

    for label, (name, want) in {
            "Gorgoroth is a waste":        ("Gorgoroth", ("high_plateau", "desert", "steppe_plateau", "mountain")),
            "Mirkwood is forest":          ("Mirkwood", ("forest_plain", "forest_hills", "forest_upland")),
            "Rohan is grass":              ("Rohan", ("steppe_plain", "plain", "farmland", "hills")),
            "Caradhras is a mountain":     ("Caradhras", ("mountain", "high_mountain")),
            "the Shire is settled":        ("Hobbiton", ("farmland", "plain", "hills")),
            "the Dead Marshes are marsh":  ("Dead Marshes", ("marsh_plain",)),
            "Forochel is cold":            ("Forochel", ("tundra", "taiga")),
            "Near Harad is dry":           ("Near Harad", ("desert", "steppe_plain", "savanna", "steppe_plateau", "hills")),
    }.items():
        got = W.zone_at(*at(name))[1]
        check("terrain", got in want, f"{label} — got {got}")

    for label, (a, b, boat, want_ok) in {
            "Hobbiton to Minas Tirith on foot": (at("Hobbiton"), at("Minas Tirith"), "none", True),
            "Mithlond to Umbar on foot":        (at("Mithlond"), at("Umbar"), "none", True),
            "Esgaroth to Rivendell on foot":    (at("Esgaroth"), at("Rivendell"), "none", True),
            "Dol Amroth to Tolfalas on foot":   (at("Dol Amroth"), at("Tolfalas"), "none", False),
            "Dol Amroth to Tolfalas by ship":   (at("Dol Amroth"), at("Tolfalas"), "ship", True)}.items():
        pts, ok, _wet = router.find(a, b, boat, cost_at=W.terrain_speed)
        check("routing", ok == want_ok, f"{label}: reachable={ok}, expected {want_ok}")

    # Tolkien's own journeys, loosely — the model is tuned to history, not to
    # Shadowfax, so the story's figures are a floor and the model sits above
    # them. Frodo took 27 days from Bag End to the Ford of Bruinen, with the
    # Old Forest and a knife in him; the Rohirrim rode a hundred leagues from
    # Dunharrow to the Pelennor in six; Gandalf did Edoras to Minas Tirith in
    # three nights on the greatest horse there ever was.
    d = hours(origin="Hobbiton", dest="Rivendell", mode="foot") / 24
    check("benchmark", 20 <= d <= 34, f"Hobbiton to Rivendell on foot — got {d:.1f} days")
    d = hours(origin="Dunharrow", dest="Minas Tirith", mode="horse", rest="low", party=6000) / 24
    check("benchmark", 6 <= d <= 14, f"the ride of the Rohirrim — got {d:.1f} days")
    d = hours(origin="Edoras", dest="Minas Tirith", mode="horse", rest="low", mount="otherworldly",
              register="saga") / 24
    check("benchmark", 3 <= d <= 9, f"Shadowfax from Edoras to Minas Tirith — got {d:.1f} days")


if WORLD == "earth":
    # ── 3. the historical rates the model is tuned to ──────────────────────────
    def per_day(**kw):
        r = W.run(Args(**kw))
        return r["travelled_km"] / max(r["travel_days"], 1)


    BENCH = [
        ("Roman iter iustum on foot, good road, 25-35 km/day",
         dict(origin="Paris", dest="Orleans", mode="foot", roads="roads"), 25, 35),
        ("Sigeric's pilgrimage rate, 22-30 km/day",
         dict(origin="Paris", dest="Rome", mode="foot", roads="roads"), 22, 30),
        ("sustained mounted travel, 50-70 km/day",
         dict(origin="Vienna", dest="Budapest", mode="horse"), 50, 70),
        ("courier with remounts, 90-140 km/day",
         dict(origin="Vienna", dest="Budapest", mode="horse_remount", rest="low"), 90, 140),
        ("ox-cart on the flat, 22-35 km/day",
         dict(origin="Budapest", dest="Vienna", mode="cart"), 22, 35),
        ("Alpine crossing on foot, 10-16 days",
         dict(origin="Geneva", dest="Milan", mode="foot"), None, None),
    ]
    for label, kw, lo, hi in BENCH:
        if lo is None:
            continue
        v = per_day(**kw)
        check("benchmark", lo <= v <= hi, f"{label} — got {v:.1f}")

    days = hours(origin="Geneva", dest="Milan", mode="foot") / 24
    check("benchmark", 10 <= days <= 16, f"Alpine crossing on foot — got {days:.1f} days")

    # ── 4. the land mask ───────────────────────────────────────────────────────
    # The mask is the one thing with no external source to check against here, so
    # it is checked from the inside: every place in the gazetteer must be on land,
    # every named sea must be sea, every named land area must be land.
    from gazetteer import is_land, landmass, LATS, LONS, NAMES  # noqa: E402
    import router  # noqa: E402

    # An eleven-kilometre raster cannot hold a harbour town on a narrow spit, so a
    # small tail of places lands wet and the router snaps them ashore. What matters
    # is that the tail stays small: if it grows, the mask has drifted.
    sample = range(0, len(NAMES), 37)
    wet = [NAMES[i] for i in sample if not is_land(LATS[i], LONS[i])]
    check("land mask", len(wet) <= len(list(sample)) * 0.035,
          f"{len(wet)} of {len(list(sample))} sampled places fall in the sea, e.g. {wet[:5]}")

    for label, (lo, la) in {
            "mid-Atlantic": (-30, 45), "Bay of Biscay": (-4, 45.5), "North Sea": (3, 54),
            "English Channel": (-1, 50), "western Mediterranean": (3, 39), "Adriatic": (15, 43),
            "Tyrrhenian": (11.5, 40), "Baltic": (19, 57), "Alboran": (-3.5, 36),
            "Ionian": (19, 38), "Ligurian": (8.5, 43.4), "Irish Sea": (-5.2, 53.5),
            "the Pacific": (-140, 10), "the Indian Ocean": (80, -20), "the Caspian": (51, 42),
            "the Black Sea": (34, 43), "the Red Sea": (38, 20), "the Gulf of Mexico": (-90, 25),
            "the Bay of Bengal": (88, 15), "Hudson Bay": (-85, 60), "the Caribbean": (-75, 15),
            "the South China Sea": (114, 12), "the Tasman Sea": (160, -40),
            "the Sea of Azov": (36, 46), "Lake Superior": (-87.5, 47.5),
            "Lake Victoria": (33, -1.5), "the Great Australian Bight": (131, -34)}.items():
        check("land mask", not is_land(la, lo), f"{label} is drawn as land")

    for label, (lo, la) in {
            "central Spain": (-3.7, 40.4), "the Paris basin": (2.35, 48.86), "Bavaria": (11.58, 48.14),
            "Crete": (24.9, 35.3), "Sicily": (14.0, 37.6), "Corsica": (9.1, 42.2),
            "Sardinia": (9.0, 40.2), "Ireland": (-8.0, 53.3), "Britain": (-1.5, 53.0),
            "Jutland": (9.5, 55.0), "Morocco": (-6.0, 33.0), "Tunisia": (9.5, 35.5),
            "the Sahara": (10, 25), "the Amazon": (-60, -3), "the Gobi": (104, 43),
            "Panama": (-79.5, 9.0), "Sinai": (33.5, 29.5), "the Deccan": (77, 17),
            "Kansas": (-99, 38), "the outback": (133, -24), "Siberia": (100, 62),
            "the Piedmont": (-78.6, 35.8), "the Altiplano": (-68, -17),
            "Hokkaido": (142.5, 43.3), "Tasmania": (146.8, -42.0)}.items():
        check("land mask", is_land(la, lo), f"{label} is drawn as sea")

    # what can be walked to, and what cannot
    for label, (a, b, same) in {
            "Madrid and Beijing are one landmass": ((40.4,-3.7), (39.9,116.4), True),
            "Madrid and London are not":           ((40.4,-3.7), (51.5,-0.13), False),
            "New York and Lima are one landmass":  ((40.7,-74.0), (-12.0,-77.0), True),
            "Tokyo and Beijing are not":           ((35.7,139.7), (39.9,116.4), False),
            "Cairo and Cape Town are one landmass":((30.0,31.2), (-33.9,18.4), True),
            "Sydney and Jakarta are not":          ((-33.9,151.2), (-6.2,106.8), False),
    }.items():
        check("landmass", (landmass(*a) == landmass(*b)) == same, label)

    # the terrain grid says something sensible about ground we know
    for label, (la, lo, want) in {
            "the Sahara is desert":        (25, 10, ("desert","sand_sea")),
            "the Amazon is rainforest":    (-3, -60, ("rainforest",)),
            "Tibet is high ground":        (32, 88, ("high_plateau","high_mountain","mountain")),
            "the Alps are mountains":      (46.5, 10.5, ("mountain","high_mountain","forest_upland")),
            "the Great Plains are open":   (41.3, -100.0, ("plain","farmland","steppe_plain")),
            "northern Siberia is cold":    (70, 100, ("tundra","taiga")),
            "the Congo is rainforest":     (0, 22, ("rainforest",)),
    }.items():
        got = W.zone_at(la, lo)[1]
        check("terrain", got in want, f"{label} — got {got}")

    # ── 5. the router keeps them out of the water ──────────────────────────────
    for label, (a, b, boat, want_ok) in {
            "Madrid to London on foot": ((40.4, -3.7), (51.5, -0.13), "none", False),
            "Madrid to London by ferry": ((40.4, -3.7), (51.5, -0.13), "ferries", True),
            "Gredos to Berlin": ((40.25, -5.3), (52.52, 13.4), "none", True),
            "Cairo to the Cape": ((30.0, 31.2), (-33.92, 18.42), "none", True),
            "Paris to Beijing": ((48.86, 2.35), (39.9, 116.4), "none", True)}.items():
        pts, ok, _wet = router.find(a, b, boat, cost_at=W.terrain_speed)
        check("routing", ok == want_ok, f"{label}: reachable={ok}, expected {want_ok}")
        if ok and boat == "none":
            wet = [p for p in pts if not router.is_land_cell(*router.cell_of(*p))]
            check("routing", not wet, f"{label} walks over water at {wet[:1]}")

    # a sea crossing must actually be shorter than walking round it
    by_land = hours(origin="Split", dest="Ancona", mode="foot")
    by_sea = hours(origin="Split", dest="Ancona", mode="foot", boat="ship")
    check("routing", by_sea < by_land,
          f"a ship should beat walking round the Adriatic: {by_sea/24:.1f}d vs {by_land/24:.1f}d")

else:
    BENCH = []
    middle_earth_checks()

# ── report ─────────────────────────────────────────────────────────────────
total = (len(ROUTES) * len(MODES) * 2 + len(ROUTES) * 9 + len(BENCH)
         + len(W.PLACES) + 45)
if failures:
    print(f"{len(failures)} FAILED of ~{total} checks\n")
    for f in failures[:25]:
        print("  ✗", f)
    if len(failures) > 25:
        print(f"  ... and {len(failures)-25} more")
    sys.exit(1)
print(f"all ~{total} checks passed")
