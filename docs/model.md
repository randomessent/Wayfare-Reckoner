# The Wayfare model

Every figure below is a modelling choice, not a measurement. They were chosen
to land on documented pre-modern travel rates and then nudged until the
benchmark journeys at the bottom came out right.

## 1. Distance

Great-circle distance between city centres, then multiplied by a **sinuosity
factor** — how much longer the walkable path is than the crow-flight line.
This is the single most important idea in the model. In a world without
engineered roads there is almost never a straight way to anywhere: you detour
around ridges, follow a river to a fording point, skirt a bog.

Typical whole-journey ratios come out at 1.10–1.15 on plains with surviving
roads and 1.55–1.75 through high mountains in pathless country. Real medieval
road distances run roughly 1.2–1.4× the crow-flight line, so the model
brackets reality and pushes past it where the premise says roads are gone.

Waypoints (`--via`) exist because a straight line from Lyon to Zagreb runs
over the Alps, and a real traveller would go around by the Po valley. The
model reads terrain, not sense.

## 2. Terrain

The route is cut into ~15 km slices. Each slice's midpoint is looked up in a
**0.1° terrain grid** — 3600 × 1800 cells, about eleven kilometres — to get a
terrain type, which supplies a sinuosity factor, a speed multiplier, and a
weather-exposure factor.

The grid is derived rather than drawn. Ruggedness comes from **ETOPO 2022**:
mean elevation and local relief for every cell, thresholded into flat, hilly,
upland, mountain and high mountain. Cover comes from a **biome layer** — the
tropics, taiga and tundra by latitude, Natural Earth's deserts by name, and
about 340 hand-authored polygons for everything in between — because nothing
in the available data tells forest from grassland. Crossing the two gives the
terrain type: relief says *hills*, biome says *wooded*, the cell is wooded
hills. It replaced a set of hand-drawn boxes that were adequate for Europe at
close range and, at continental scale, put Kansas in the Rockies.

| Terrain | Sinuosity | Speed | Exposure |
|---|---|---|---|
| river valley road | 1.12 | 1.03 | 0.95 |
| open plain | 1.14 | 1.00 | 1.10 |
| settled farmland | 1.16 | 1.00 | 1.15 |
| arid plateau | 1.16 | 0.95 | 1.05 |
| coastal lowland | 1.22 | 0.94 | 1.05 |
| rolling hills | 1.24 | 0.88 | 1.00 |
| lowland forest | 1.24 | 0.86 | 0.85 |
| high moorland | 1.32 | 0.80 | 1.25 |
| wooded hills | 1.32 | 0.78 | 0.90 |
| marsh and delta | 1.34 | 0.72 | 1.45 |
| karst coast | 1.38 | 0.72 | 1.10 |
| forested uplands | 1.38 | 0.72 | 0.95 |
| mountains | 1.55 | 0.63 | 1.30 |
| high mountains | 1.62 | 0.55 | 1.55 |

The mountain speed figures are consistent with Naismith's rule once ascent is
folded in: roughly 2.4 km/h effective for a walker in real mountains, against
4.3 km/h on the flat.

## 3. Pace

Base paces are **kilometres per hour of actual movement**, not per hour
elapsed. Halts, meals, and camp are handled separately by the rest regime.

| Mode | Pace | Sustainable hours/day | Hard days before a halt |
|---|---|---|---|
| on foot | 4.3 | 8.0 | 8 |
| on foot with baggage | 3.6 | 7.5 | 7 |
| on horseback | 8.0 | 9.0 | 6 |
| on horseback with remounts | 9.8 | 10.0 | 9 |
| with carts | 3.2 | 8.0 | 8 |

The mounted pace assumes an endurance-bred horse alternating walk (~6 km/h)
and trot (~13 km/h), with the rider dismounting to lead on climbs. Canter and
gallop are deliberately absent from the sustained figure: a gallop is 40 km/h
for two or three kilometres and then the horse is done for the day. Treat
galloping as a scene, not a travel rate.

Carts are additionally penalised by 30% distance and 30% speed in mountains,
marsh, karst and forested uplands — wheels have to go the long way round.

## 4. Rest regimes and fatigue

| Regime | Hours moving | Night travel | Path |
|---|---|---|---|
| high — Unhurried | 6.0 | no | ×1.06 (they wander) |
| medium — Purposeful | 8.0 | no | ×1.00 |
| low — Driven | 13.0 | yes | ×0.98 |

Purposeful is deliberately set at a pace a party can hold week after week —
about 30 km a day on foot, 58 on horseback, both inside the documented bands.
Set it any higher and Driven has no headroom left to be worth doing.

Two separate things happen when a party pushes past its sustainable hours.

**Fatigue** scales speed down. It accrues at `(hours moved − sustainable) ×
0.006` a day, and each night gives back `0.010 + 15% of what's there`. The
proportional term is what matters: tiredness settles at a plateau — around 9%
for a driven rider — instead of compounding until the party grinds to a halt.

**Strain** counts consecutive days pushed past the limit. When it reaches the
mode's hard-day count the party loses a full day and strain resets. That is
the honest cost of a forced ride: a horse worked thirteen hours a day needs a
day down after about six of them, and no amount of willpower substitutes.

Splitting the two matters. When both jobs were done by one runaway variable,
a driven party could arrive *later* than a purposeful one — the speed penalty
and the halts together ate more than the extra five hours a day bought. That
is nonsense, and `scripts/selftest.py` now asserts it can't happen.

## 5. Daylight, departure, and night travel

Daylight is computed properly from the route's mean latitude and a
season-representative solar declination (±21° at the solstices, ±4° at the
equinoxes). At 46°N that gives ~15.1 h in summer and ~8.9 h in winter — which
is why winter journeys stretch even in fair weather: the day's hour budget is
capped by the sun.

Departure time sets the clock. Leaving at 04:00 buys most of a marching day;
leaving at 16:00 buys two hours. Departing in darkness with night travel off
simply waits for dawn and costs no travel day.

Night movement runs at **55%** of daylight speed and is only permitted under
the driven regime unless forced with `--night`.

## 6. Weather

Weather scales speed, and terrain exposure decides how hard it bites: the same
downpour costs a delta far more than a forest track. The shortfall from clear
weather is multiplied by the terrain's exposure factor.

| Weather | Speed | Chance a given day is lost outright |
|---|---|---|
| clear | 1.00 | — |
| grey and dry | 0.99 | — |
| hard wind | 0.94 | — |
| fog | 0.80 | 2% |
| intermittent rain | 0.93 | — |
| heavy rain | 0.74 | 4% |
| storms | 0.55 | 14% |
| punishing heat | 0.85 | 3% |
| snow | 0.58 | 8% |
| deep snow | 0.34 | 20% |

Winter additionally closes the high passes: high-mountain slices take a
further ×0.68 speed and ×1.15 distance penalty.

## 7. Party size and fantasy dials

Party factor: 1–3 travellers ×1.00, 4–10 ×0.97, 11–30 ×0.92, 31–100 ×0.85,
more ×0.78. Columns move at the pace of their slowest element and spend real
time forming up and watering.

Mount quality shifts both speed and sustainable hours: ordinary stock ×0.94
and −1 h, endurance-bred ×1.00, exceptional bloodstock ×1.10 and +1 h,
otherworldly ×1.30 and +3 h.

Hazard level adds expected delay days as a fraction of marching days — 2% for
low, 5.5% moderate, 11% high — for bandits, washed-out fords, a lamed horse, a
lord's toll. This lands in the gap between the expected and bad-luck figures
rather than in the headline.

## 8. Finding a way

Until routing existed the model drew a great-circle line and asked what terrain
lay under it. That is fine across France and nonsense across the Bay of Biscay.

Now an **A\* search over a tenth-of-a-degree land mask** (3600 × 1800 cells,
about eleven kilometres) finds the way first. Step cost is distance divided by
the terrain's speed factor, so the search prefers a river valley to a ridge.
The path is then simplified to a handful of waypoints and handed to the same
segment model as before.

This splits the problem honestly. **A\* answers "which way would they go"** —
around a sea, along a valley, through a pass. **Sinuosity answers "how much
does the path wander within that"** — the detours an eleven-kilometre cell
cannot see. Neither double-counts the other.

Eleven kilometres is a fine mesh, and a crossing of Eurasia is several million
cells: a plain great-circle heuristic makes A\* fan out across a continent. So
each search is run twice. First a **half-degree grid is flooded outward from
the destination**, giving every neighbourhood a lower bound on what remains;
that grid counts a cell as land if any fine cell in it is land, which makes the
bound optimistic, which is exactly what an admissible heuristic needs. The fine
search then walks nearly straight. Lisbon to Beijing takes about two seconds
instead of most of a minute.

Two lookups come before either search. Every cell carries the number of the
**walkable landmass** it belongs to, so a party that will not get its feet wet
is told Madrid to London is impossible without searching half of Europe first.
And the mask has the narrow waters an eleven-kilometre raster welds shut
painted back open — Gibraltar, Dover, Messina, the Bosphorus, the Dardanelles,
the Danish belts, Kerch, Bab el Mandeb, Hormuz, Malacca, Sunda, Bass, Cook,
Tsugaru, Korea, Bering, Bonifacio, Otranto — and the canals nobody in this
world dug, Suez and Corinth, forced back to land.

One artefact is worth knowing about. Between two waypoints the model still
draws a great circle, and near a coast that chord can clip a bay the router
carefully walked around. So when the party has no boat, water under a chord is
read as land — the router already proved a dry path exists, and the chord is
simply too coarse to draw the headland.

### Water

`none` makes water impassable and a blocked route is reported as blocked.
`ferries` and `ship` make it passable at a cost per kilometre stiff enough to
shape behaviour by itself: at the ferry rate a 30 km strait is worth it and the
Adriatic is not, which is what "ferries at the narrow places" should mean
without any special-casing of straits. A ferry is additionally held to water
within about ninety kilometres of a shore — a boatman will put you across a
strait and will not take you to Greenland — so ferries reach Sicily and Tunis
and never reach America.

At sea the day is 20 hours, not 8 or 13 — a ship keeps watches — and no strain
accrues, because nobody is walking. Embarkation costs 6 hours by ferry, 12 by
ship: the tide, and finding a boatman.

## 9. The chart

The browser app draws the route in **EPSG:3857** (spherical Web Mercator), so
the graticule is rectilinear and the terrain zones — which are lat/lon boxes —
stay rectangles rather than trapezoids.

The coastline is **Natural Earth 10m** land and lakes, generalised to about six
kilometres — 1,055 land rings and 900 lake rings, drawn with an even-odd fill so
a ring that wraps a peninsula does not cancel itself.

The ground inside it is not drawn at all. It is **painted pixel by pixel from
the terrain grid**: one pass over the visible pixels, each asking the grid what
it is standing on, with cells that are sea left clear so the ocean shows
through. What the chart shows is therefore exactly what `zone_at()` returned,
including how coarse it is. A borrowed basemap would have hidden that, which is
the reason there isn't one.

Region names are placed in the same pass. The centroid alone will not do —
Italy's centroid is in the Adriatic — so a scattering of the actual land pixels
carrying each name is kept, and the label goes to whichever of those sits
nearest the middle.

With 171,000 settlements, drawing every one would be a grey smear, so the
population a place needs to earn a dot rises with the width of the view: a
continent gets capitals, a valley gets villages, and the night's camps are
always drawn whatever their size.

## 10. Register and world scale

These two are the fantasy dials, kept separate on purpose because they answer
different questions.

**World scale** multiplies every distance. It is not a fudge factor for the
model — it is a statement about the map. Invented continents are almost always
larger and emptier than the real one they borrow their shape from, and a
setting where Lyon to Zagreb is a two-month ride rather than a three-week one
is a different setting. Scale says so explicitly instead of hiding it in the
terrain tables.

**Register** governs the country between the towns and the people crossing it:

| | Wilderness | Endurance | Fatigue rate | Hazard floor | Mounts |
|---|---|---|---|---|---|
| Chronicle | ×1.00 | +0 | ×1.00 | none | mundane, endurance-bred |
| Romance | ×1.06 | +0.5 h | ×0.85 | low | + exceptional |
| Saga | ×1.14 | +1.5 h | ×0.65 | moderate | + otherworldly |

Wilderness multiplies the sinuosity factor: the higher the register, the less
the map is to be trusted and the further the real path wanders from the line.
Endurance raises the hours a party can move before fatigue accrues; the
fatigue rate scales how fast it accrues past that. Together they decide how
often a driven party is forced to halt — five times over Lyon to Zagreb as a
chronicle, not at all as a saga.

Chronicle is the honest historical model: with it selected, nothing in the
output depends on a modifier a 12th-century itinerary could not vouch for.
Everything above chronicle is a deliberate departure, and the report names
which register produced it.

## 11. Benchmarks

Tuned so that, with `--roads roads --rest medium` (the closest thing to a
functioning road network):

- **Paris → Orléans on foot:** ~29 km/day, against a Roman *iter iustum* of
  ~30 km.
- **Geneva → Milan on foot, summer:** 14 days over ~344 km. Alpine crossings
  by the Great St Bernard took pilgrims around two weeks.
- **Paris → Rome on foot, good road:** ~27 km/day, against Sigeric's 990 AD
  itinerary of Rome → Canterbury in 79 stages at ~25 km/day. On mixed ground
  the same journey drops to ~22 km/day, which is the de-roading premise
  showing up in the number.
- **Vienna → Budapest on horseback:** 3 days at 60 km/day. Sustained mounted
  travel is documented at 50–70 km/day.
- **Vienna → Budapest with remounts, driven:** ~118 km/day. The Roman *cursus
  publicus* managed 80 km/day routinely and far more in emergencies.

All six are asserted as ranges in `scripts/selftest.py`, so a tuning change
that quietly breaks one fails the suite instead of shipping.
- **Budapest → Vienna by cart:** 8 days at 30 km/day, stretching to 12 in
  heavy rain. Ox-cart and wagon rates of 25–35 km/day are well attested, and
  mud is the classic killer.
