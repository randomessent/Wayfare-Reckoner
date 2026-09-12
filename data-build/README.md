# Building the data

Nothing here runs at journey time. These scripts turn four public datasets into
the four files in `data/`, and are kept so the grids can be rebuilt or refined
rather than merely trusted.

| Source | Used for |
|---|---|
| GeoNames `cities1000` (CC BY 4.0) | every settlement above 1,000 people |
| Natural Earth 10m `land`, `lakes` (public domain) | the coastline and the land mask |
| Natural Earth 10m `geography_regions_polys` | 1,034 named physical regions |
| ETOPO 2022 60-arc-second surface (NOAA) | elevation and local relief |

The ETOPO GeoTIFF is 21600 × 10800 and far too large to carry, so it is reduced
first — 6 × 6 source pixels block-averaged into a 0.1° mean elevation and a 0.1°
relief array — and only those two arrays are used here.

Run in order:

```bash
python3 land.py          # landmask_0p1.npy from NE land minus lakes
python3 mask01.py        # the routing mask: straits forced open, canals shut
python3 terrain.py       # terrain_0p1.npy, names_0p1.npy, names.json
python3 comps.py         # comps_0p1.npy — which walkable landmass each cell is
python3 places_build.py  # places_all.json from GeoNames + curated landmarks
python3 export.py        # data/: places.tsv, grids.json, coastline.json, regions_table.json
python3 emit_js.py       # the same four, packed into one JavaScript source
```

## Middle-earth

A second, much smaller pipeline, in one script:

```bash
pip install numpy pillow pyshp
python3 data-build/build_middle_earth.py     # data/middle-earth/, in a few seconds
```

It wants, under `sources/middle-earth/`:

| What | Where from |
|---|---|
| `ME-GIS/` | a clone of https://github.com/andrewheiss/ME-GIS — coastline, lakes, forests, wetlands and the named points, as shapefiles |
| `10k.jpg`, `10k.wld` | `data/rasters/` in https://github.com/bburns/Arda — the ME-DEM elevation model as a byte-per-pixel JPEG, and its world file |

The script's docstring explains how the frame is placed on the globe and how
the raster's bytes are read as metres. `me_regions.py` holds the hand-drawn
outlines — countries, settled land, grasslands, deserts, the far north —
and `me_places.py` the second names everything in Tolkien has, plus the few
places a reader will ask for that the layers have no point for. It also
writes `middle_earth_preview.png` beside itself, which is the quickest way
to see whether a border you moved went where you meant.

`eu_boxes.py` holds the old provincial rectangles for Europe — Burgundy, the
Ebro Valley, Wessex — which Natural Earth does not name. `../scripts/regions.py`
holds the hand-drawn biome polygons, and `../scripts/places.py` the curated
landmarks. Those three are hand-authored; everything else is derived.
