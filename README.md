# Happy Roads place data

Builds the places the Happy Roads app downloads by region (fuel stations, tolls, speed cameras,
ΚΤΕΟ, rest areas, parking, EV charging, workshops) from Geofabrik's OpenStreetMap extracts.
The design is in the app repository: `docs/superpowers/specs/2026-10-10-global-region-data-design.md`.

    py -3.13 -m venv .venv && .venv/Scripts/python -m pip install osmium shapely pytest
    .venv/Scripts/python -m happyroads_data.build --country gr --extract greece-latest.osm.pbf --out out --version 2026-10

Data © OpenStreetMap contributors, ODbL.
