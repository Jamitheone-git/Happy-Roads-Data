# Happy Roads place data

Builds the places the [Happy Roads](https://github.com/Jamitheone-git/Happy_Roads) app downloads by
region (fuel stations, tolls, speed cameras, ΚΤΕΟ, rest areas, parking, EV charging and workshops)
from [Geofabrik](https://download.geofabrik.de/)'s OpenStreetMap extracts. It publishes them as
static files on Cloudflare R2, at `happyroads.data.tumeechu.com/v1/`.

## Running it

- **Every month**, `.github/workflows/build.yml` builds every country Geofabrik offers, one job
  each, and publishes the index last. A country that fails keeps last month's data.
- **By hand**, from the repository's Actions tab, choose *Build place data* and then *Run workflow*.
  The *countries* field takes ISO codes (`gr,cy,at`); leave it empty for every country.
- **One country locally**, with Python 3.13:

      py -3.13 -m venv .venv && .venv/Scripts/python -m pip install osmium shapely boto3 pytest
      .venv/Scripts/python -m happyroads_data.build --country gr --extract greece-latest.osm.pbf --out out --version 2026-10

  `python -m pytest` runs the tests. Uploading needs a `.env` holding the R2 credentials, which is
  never committed.

After a run, `python tools/report.py <run id>` lists the countries worth a look: failed, one
region, or places lost.

## Where things are set

- `levels.toml` sets the OSM admin level each country is divided at. A country it does not name
  starts at 4, and climbs to 5 to 8 if 4 gives it no regions.
- `aliases/` keeps the ids the app already shipped for Greece, and countries' names where OSM
  has none.
- `geofabrik.toml` lists the countries built from their subdivisions' files (the United States),
  and settles the codes Geofabrik gives more than one extract.

## Data licence

© OpenStreetMap contributors, under the [Open Database License](https://www.openstreetmap.org/copyright).
The published files are a derived database under the same licence.
