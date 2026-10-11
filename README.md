# Happy Roads place data

The generator behind the places the [Happy Roads](https://github.com/Jamitheone-git/Happy_Roads) app
downloads by region: fuel stations, tolls, speed cameras, vehicle inspection centres (ΚΤΕΟ), rest
areas, parking, EV charging and workshops.

It reads a country's OpenStreetMap extract from [Geofabrik](https://download.geofabrik.de/). It
cuts the country into regions along their real administrative borders, and writes one small gzip
file per region and kind of place. The app downloads these as plain static files from Cloudflare R2.
It never queries a live map server, so a busy public server can no longer fail a driver's download.

The design, and the reasoning behind it, is in the app repository:
`docs/superpowers/specs/2026-10-10-global-region-data-design.md`.

## What it produces

```
out/v1/index.json                        the countries: id, names, bounding box, version
out/v1/<cc>/manifest.json                one country's regions
out/v1/<cc>/<regionId>/<layer>.json.gz   one layer of one region
```

- **`<layer>`** is one of `fuel`, `toll`, `camera`, `inspection`, `restArea`, `parking`,
  `charging`, `workshop`, the app's own `PlaceLayer` names.
- **A layer file** is `{"<layer>": [[lat, lon, name?, kind?, attributes?], ...]}`, with trailing
  empty fields left off. A layer with no places is still written, as `{"<layer>": []}`. The app
  relies on that to tell "asked, and there are none" from "never downloaded".
- **A manifest region** is `{id, name, names, neighborIds, fileUrl, version, bounds}`.
  - `fileUrl` is the region's folder relative to `v1/`.
  - `bounds` is `[south, west, north, east]`.
  - The first entry is the whole country. It has `parts` instead of bounds, and the app gathers it
    from its parts.
- **`version`** is the build month (`2026-10`).
- **`v1/`** lets a future format be published beside this one, while installed copies of the app
  keep reading the old one.

Gzip is written with a fixed timestamp, so the same places always give the same bytes. That lets
the upload skip every file that did not change.

## Running it

Python 3.13 (3.14 has no `osmium` wheel yet):

```bash
py -3.13 -m venv .venv
.venv/Scripts/python -m pip install osmium shapely boto3 pytest

curl -L -o greece-latest.osm.pbf https://download.geofabrik.de/europe/greece-latest.osm.pbf
.venv/Scripts/python -m happyroads_data.build --country gr --extract greece-latest.osm.pbf --out out --version 2026-10
```

Greece takes about three and a half minutes. The result is 70 regions, about 28 000 places and
1.5 MB.

### Publishing

```bash
.venv/Scripts/python -m happyroads_data.upload --out out
```

The upload reads its credentials from a `.env` file in the repository root. That file is ignored
by git and must never be committed:

```
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_ENDPOINT=https://<account>.r2.cloudflarestorage.com
R2_BUCKET=happy-roads-data
```

Files are published in an order a reader cannot trip over:

1. the region files,
2. then the manifests that name them,
3. then the index that names the manifests.

So a phone reading mid-upload is never sent to a file that is not there yet. A file whose bytes
match what is already in the bucket is not sent again.

### Checking a build against Overpass

```bash
.venv/Scripts/python tools/compare_overpass.py out
```

For every Greek region, this asks OpenStreetMap's Overpass API for the same places inside the same
border, and compares the counts layer by layer. It is the check that proved the generator before
the app was switched to it. On the first run, 58 of 70 regions matched exactly, and the rest were
one to four places short, which is what two days of OSM edits look like.

The public servers refuse often, so the script alternates between two of them and caches what they
answered. A stopped run picks up where it was.

## How a country is cut into regions

- **`levels.toml`** names the OSM `admin_level` each country is divided at. `admin_level` means
  something different in every country. A country that is not listed takes the default, level 4.
  A country that comes out badly is fixed by one line there.
- **`aliases/<cc>.toml`** keeps region ids a device may already hold. A downloaded region is
  remembered by its id, so an id must never change between builds.
  - A region with no alias is `<cc>-<OSM relation id>`, which OSM keeps stable.
  - Greece keeps the slugs the app shipped with (`achaia`, `athens`, …), its names, and its
    hand-checked neighbours. `athens` is the union of five relations. The file was generated once
    by `tools/import_greek_aliases.py`.
  - A missing alias relation stops the build rather than quietly orphaning every download of that
    region.
- **Places go into a region by point-in-polygon** against its true border. A place in no region is
  dropped, for example one offshore, or one just across the frontier that Geofabrik's margin let
  in. A county of a neighbouring country that arrives whole in the extract is left out the same
  way.
- **Neighbours** are regions sharing at least 1 km of border, so a corner or a strip of sea does
  not make one. Neighbours only drive the picker's colour hint. A country whose alias file lists
  neighbours uses that list instead.

The tag rules (which OSM tags make a fuel station, a toll, and so on) are a port of the app's
`lib/core/data/osm_layers.dart`. `tests/test_drift.py` fails when the two disagree. It runs only
when `HAPPYROADS_APP` points at a checkout of the app.

## Tests

```bash
.venv/Scripts/python -m pytest
HAPPYROADS_APP=../HappyRoads .venv/Scripts/python -m pytest tests/test_drift.py
```

The tests run on a hand-made extract, `tests/fixtures/two_squares.osm`, and need no network.

## Known limits

- **Not every country will be good.** Some have few tags in OSM or unusual administrative levels,
  and some have no Geofabrik extract.
- **Data is up to a month old.**
- **A region crossing the antimeridian** (Chukotka, Fiji) has no correct bounding box. It will be
  written without one, so its map cannot be kept offline.
- **Only Greece has been built so far.** A monthly GitHub Actions workflow for every country is
  the next step.

## Data licence

The data is © OpenStreetMap contributors, available under the
[Open Database License](https://www.openstreetmap.org/copyright). The app credits it on every map.
