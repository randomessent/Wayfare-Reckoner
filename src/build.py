#!/usr/bin/env python3
"""Stitch the app together.

    python3 src/build.py

Reads the pieces in this folder and the four files in `data/`, and writes
`index.html` at the top of the repo — one self-contained file that opens in any
browser with no server and no network. Everything the app needs, the gazetteer
and the grids included, is carried inside it, which is why it is about ten
megabytes.

It is called `index.html` rather than something more descriptive because that
is the name GitHub Pages serves at the bare URL. Publishing the repo therefore
publishes the app, with no configuration beyond turning Pages on.

Run this after changing anything in `src/`. If you have changed the data
itself, run the pipeline in `data-build/` first.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

# order matters: the data first, then the layers that build on it
PARTS = ["grid.js", "places.js", "route.js", "engine.js", "mapview.js", "ui.js"]


def read(*path):
    with open(os.path.join(*path), encoding="utf-8") as fh:
        return fh.read()


# Every world the app knows: its four data files, and the few things about it
# that are not data — what to call it, how to draw it, what to suggest. The
# earth is first and is the default.
WORLDS = [
    dict(key="earth", folder=DATA, label="Our own earth",
         proj="mercator", pops=True, customKey="wayfare.places.v2",
         examples=[["Lyon", "Zagreb"], ["Sierra de Gredos", "Burgos"],
                   ["Raleigh", "Santa Fe, New Mexico"], ["Samarkand", "Kashgar"],
                   ["Cairo", "Timbuktu"]],
         note="The whole earth at a tenth of a degree: 170,932 settlements from GeoNames, "
              "Natural Earth's coastline, terrain derived from ETOPO elevation.",
         holds="settlements, ranges, forests, passes and parks",
         mapNote="Web Mercator (EPSG:3857). The coastline is Natural Earth's, generalised to about six "
                 "kilometres;",
         credit="GeoNames cities1000 (CC BY 4.0), Natural Earth (public domain), ETOPO 2022 (NOAA)."),
    dict(key="middle-earth", folder=os.path.join(DATA, "middle-earth"), label="Middle-earth",
         proj="middle-earth", pops=False, customKey="wayfare.places.middle-earth.v1",
         examples=[["Hobbiton", "Rivendell"], ["Bree", "Minas Tirith"],
                   ["Edoras", "Helm's Deep"], ["Minas Tirith", "Mount Doom"],
                   ["Mithlond", "Erebor"]],
         note="Tolkien's Middle-earth from the ME-DEM project's map layers: the coast, the "
              "forests and marshes as drawn, terrain from their elevation model, and some seven "
              "hundred named places. Hobbiton sits at the latitude of Oxford, as its author said it did.",
         holds="towns, strongholds, ruins, ranges, forests, passes and fords",
         mapNote="The map as the ME-DEM team drew it — a kilometre grid pinned to the globe at the "
                 "Shire, so distances are true and the country keeps its shape. The coastline is theirs;",
         credit="ME-GIS layers and elevation model by the ME-DEM team (monks, SeerBlue, Redrobes, "
                "jvangeld), used with permission."),
]


def data_script():
    """Every world's four data files, as one JavaScript source.

    `places.tsv` goes in as a JSON string rather than raw text: it is tab- and
    newline-separated and full of apostrophes, and JSON's escaping is the one
    that is certain to survive being pasted into a script tag.
    """
    out = ["/* Data, one entry per world, built to a tenth of a degree — about eleven km. */",
           "const WORLDS = {};"]
    for w in WORLDS:
        meta = {k: v for k, v in w.items() if k != "folder"}
        out += [
            f"/* {w['label']}: {w['credit']} */",
            f"WORLDS[{json.dumps(w['key'])}] = {{",
            "  meta: " + json.dumps(meta, ensure_ascii=False) + ",",
            "  grids: " + read(w["folder"], "grids.json") + ",",
            "  coast: " + read(w["folder"], "coastline.json") + ",",
            "  regions: " + read(w["folder"], "regions_table.json") + ",",
            "  placesTsv: " + json.dumps(read(w["folder"], "places.tsv"), ensure_ascii=False) + ",",
            "};",
        ]
    return "\n".join(out)


def main():
    out = [read(HERE, "head.html"), read(HERE, "body.html"), "<script>", data_script()]
    out += [read(HERE, p) for p in PARTS]
    out.append("</script>")
    blob = "\n".join(out)

    dest = os.path.join(ROOT, "index.html")
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(blob)
    print(f"wrote {os.path.relpath(dest, os.getcwd())} — {len(blob.encode('utf-8'))/1e6:.1f} MB")


if __name__ == "__main__":
    main()
