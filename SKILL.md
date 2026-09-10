---
name: wayfare
description: Estimate how long an overland journey takes in a pre-modern or fantasy world — on foot, horseback, or by cart — between any two places on earth, accounting for terrain, roads, rest regime, weather, season, party size, boats, and departure time. Returns total days and hours plus a day-by-day itinerary. Use whenever someone asks how long it would take to travel, ride, march, or walk from one place to another in a setting without modern transport.
---

# Wayfare

Answers "how long would it take them to get there?" for a world stripped of
modernity — a few surviving paved roads, cart tracks, and a great deal of
wilderness. It began as a Europe between the Iberian Peninsula and the
Hungarian plain; it now covers the whole earth at the same grain.

## Running it

```bash
python3 cli/wayfare.py --from Lyon --to Zagreb --mode horse --rest medium
```

Add `--json` for machine-readable output (same fields, useful for feeding a
table or an app).

### Options

| Flag | Values | Default |
|---|---|---|
| `--world` | `earth`, `middle-earth` | `earth` |
| `--from` / `--to` | any city in the gazetteer (case/alias tolerant) | required |
| `--via` | zero or more waypoints, in order | none |
| `--mode` | `foot`, `foot_laden`, `horse`, `horse_remount`, `cart` | `foot` |
| `--rest` | `high`, `medium`, `low` | `medium` |
| `--weather` | `clear`, `overcast`, `wind`, `fog`, `light_rain`, `heavy_rain`, `storm`, `heat`, `snow`, `deep_snow` | `clear` |
| `--season` | `spring`, `summer`, `autumn`, `winter` | `summer` |
| `--roads` | `roads`, `mixed`, `trails`, `wilderness` | `mixed` |
| `--mount` | `mundane`, `hardy`, `exceptional`, `otherworldly` | `hardy` |
| `--hazard` | `none`, `low`, `moderate`, `high` | `none` |
| `--boat` | `none`, `ferries`, `ship` | `none` |
| `--register` | `chronicle`, `romance`, `saga` | `chronicle` |
| `--scale` | world scale, `1.0` is our map | `1.0` |
| `--party` | number of travellers | `1` |
| `--depart` | clock time, e.g. `04:30`, `21:00` | `06:00` |
| `--night` / `--no-night` | force night travel on or off | by rest regime |

### Finding a way, and crossing water

The model no longer draws a straight line and asks what is under it. An A*
search over a tenth-of-a-degree land mask finds a way **across the ground**,
preferring easy going, before any time is reckoned. So Split to Ancona goes
705 km round the head of the Adriatic rather than 236 km across it, and a
route from Spain to Britain on foot comes back as impossible rather than
quietly walking the Channel.

`--boat` decides what water they can take:

| | What it allows | Sea pace | Waiting for a boat |
|---|---|---|---|
| `none` | nothing — if there is no way round, there is no way | — | — |
| `ferries` | straits and river mouths; an open sea is never worth it | 4 km/h | 6 h per crossing |
| `ship` | coasting or crossing a sea, sailing through the night | 6.5 km/h | 12 h per embarkation |

Days at sea run to 20 hours because a ship keeps watches, and nobody's legs
tire aboard, so no strain accrues. When a route is impossible the report says
so plainly and falls back to the straight line, which is a figure for
comparison and not a journey anyone could make.

### Register — how much fantasy is allowed in

Two independent dials answer "should this be as real as a modern map?".

**`--scale`** is the map itself. At `1.0` the distances are the ones you'd
measure today. At `1.5` the same two towns sit half again as far apart — a
continent bigger than ours, which is what most invented maps quietly are.
It multiplies distance and nothing else.

**`--register`** is the people and the country between the towns:

| | Wilderness | Endurance | Fatigue | Hazard floor | Mounts |
|---|---|---|---|---|---|
| `chronicle` | ×1.00 | — | ×1.00 | none | up to endurance-bred |
| `romance` | ×1.06 | +0.5 h/day | ×0.85 | low | + exceptional |
| `saga` | ×1.14 | +1.5 h/day | ×0.65 | moderate | + otherworldly |

Wilderness stretches the path further beyond the crow line — the map admits
less than the land holds. Endurance and fatigue govern how long the party can
push before a forced halt. The register also caps which mounts exist and puts
a floor under how much goes wrong: in a saga something is always out there.

The two dials pull opposite ways, which is the point. Saga makes the country
bigger *and* the travellers tougher; a driven ride from Lyon to Zagreb runs
23 days as a chronicle and 14 as a saga, over more ground.

### The rest regimes

- **high — Unhurried.** 6 h on the move. Full night's sleep, proper camp,
  meals, time to look around. They also wander: the path is ~6% longer.
- **medium — Purposeful.** 8 h on the move. Seven hours' sleep, quick camp,
  halts only to water the animals and eat cold. This is a pace a party can
  hold indefinitely — around 30 km a day on foot, 58 on horseback.
- **low — Driven.** 13 h on the move, night marching allowed. Four or five
  hours' snatched sleep. Roughly half again the daily distance, paid for in
  a slow speed penalty and a forced halt after enough days running.

Pushing harder always arrives sooner. If it ever doesn't, that's a bug —
`cli/selftest.py` asserts it across every route, mode and season.

## The chart

`index.html` is a self-contained browser version of the same
model — open it directly, no server, no network. It adds what the command
line can't draw: a chart of the route in Web Mercator (EPSG:3857), zoomable
and pannable, with a marker at each night's end, forced halts ringed, and
hover linking every marker to its row in the itinerary. Hand it to the user
when they want to *see* the journey rather than read it.

The chart's coastline is Natural Earth's 10m land and lakes, generalised to
about six kilometres — finer than anything the travel model claims. The ground
inside it is painted pixel by pixel from the same terrain grid the reckoning
walks over, so the colours on the chart are the ground that was actually
counted rather than a picture laid over it.

If you change any number in `cli/`, the app holds its own copy of the
model in JavaScript (`src/engine.js`) — update both, and rebuild with
`python3 src/build.py`, or say plainly that only the CLI changed.

## Checking the model

```bash
python3 cli/selftest.py
```

~300 assertions: that harder regimes never arrive later, that every dial
(roads, weather, season, party size, mounts, world scale, mode, departure
time) moves the answer the direction it claims, and that six historical
benchmarks still land in range. Run it after touching any number in the
model.

## How to use it in conversation

1. **Ask for what's missing.** Mode and rest regime change the answer more
   than anything else. If the user hasn't said, ask before running.
2. **Watch the route.** The search finds a way over the ground and prefers
   easy country, but it knows nothing about where the passes and fords are. If
   it takes a line a traveller would obviously not, re-run with `--via` through
   the sensible intermediate towns and say that you did.
3. **Report the headline first** — "about nineteen days" — then the texture:
   what ground dominated, where the hard days fall, what would change it.
4. **Give the range when it matters.** The output carries best case, expected,
   and bad-luck figures. Weather and hazards live in the gap between them.
5. **Don't over-trust the second decimal.** These are plausible figures for
   fiction, not survey data. Round in prose.

## Naming places

The gazetteer is GeoNames' `cities1000` — every settlement above a thousand
people, about 171,000 of them, worldwide — plus ~450 curated landmarks that
have no populated place of their own: mountain ranges, national parks, forests,
Alpine passes, lakes and coasts.

Where a name is shared, the biggest place wins, with a thumb on the scale for
seats of government: `Orleans` is the French one, not the suburb of Ottawa;
`Toledo` is Ohio, and `Toledo, Spain` is Spain. Adding the region or country
always settles it.

Lookup is deliberately forgiving. All of these resolve:

```
Avila                                              exact
Ávila, Spain                                       accents and country dropped
Parque Regional de la Sierra de Gredos, Ávila      matches "Sierra de Gredos"
Koln / Nurnberg / Wien                             local names and aliases
krumlov                                            partial name
Nurnburg                                           misspelling -> suggestions
```

**For anywhere not in the gazetteer, use coordinates.** They are accepted
everywhere a place name is:

```bash
python3 cli/wayfare.py --from "40.66,-4.70" --to "Gredos camp @ 40.25,-5.30"
```

`40.66, -4.70`, `40.66N 4.70W` and `Label @ lat,lon` all parse. The terrain
zone is read from the coordinates, so an unnamed point works exactly like a
named one. Invented places work the same way — give the label and the
coordinates you want it to sit at.

When a lookup fails the error names the closest matches. If the user asks
about a place you can't resolve, don't stop — supply its coordinates
yourself and re-run.

## The ground

`data/` carries four files, all built by the scripts in `data-build/` and all
loaded by both the CLI and the app:

| File | What it is |
|---|---|
| `places.tsv` | 170,932 places: name, position, region, population, kind, aliases |
| `grids.json` | four 3600×1800 grids at 0.1° — land, terrain, region name, walkable landmass — run-length encoded |
| `coastline.json` | 1,055 land rings and 900 lake rings for drawing |
| `regions_table.json` | the 371 interned "Province, Country" strings |

Terrain is derived, not drawn: **ruggedness from ETOPO 2022** (mean elevation
and local relief per cell), crossed with a **biome layer** — latitude bands,
Natural Earth's deserts, and ~340 hand-authored polygons — because nothing in
the available data distinguishes forest from grass. **Names come from Natural
Earth's 1,034 named physical regions**, with the smaller name always winning
over the larger one it sits inside, then a set of old provincial rectangles for
Europe, then the province of the nearest town where nothing else has a name.

The land mask forces open the narrow waters an eleven-kilometre raster welds
shut — Gibraltar, the Bosphorus, the Belts, Messina, Dover and fifteen more —
and forces shut the canals nobody in this world dug: Suez and Corinth.

Data credits: GeoNames (CC BY 4.0), Natural Earth (public domain), ETOPO 2022
(NOAA, public domain).

## Where the numbers come from

See `docs/model.md` for the full derivation: base paces, terrain
multipliers, the sinuosity factor, fatigue accrual, daylight, and the
historical benchmarks the model was tuned against.
