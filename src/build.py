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


def data_script():
    """The four data files, as one JavaScript source.

    `places.tsv` goes in as a JSON string rather than raw text: it is tab- and
    newline-separated and full of apostrophes, and JSON's escaping is the one
    that is certain to survive being pasted into a script tag.
    """
    return "\n".join([
        "/* Data. GeoNames cities1000 (CC BY 4.0), Natural Earth (public domain),",
        "   ETOPO 2022 (NOAA). Built to a tenth of a degree — about eleven km. */",
        "const GRIDS = " + read(DATA, "grids.json") + ";",
        "const COAST = " + read(DATA, "coastline.json") + ";",
        "const REGION_TABLE = " + read(DATA, "regions_table.json") + ";",
        "const PLACES_TSV = " + json.dumps(read(DATA, "places.tsv"), ensure_ascii=False) + ";",
    ])


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
