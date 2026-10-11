# Phase 4: every country, monthly, on GitHub Actions — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** A workflow that builds every country Geofabrik offers once a month and publishes it to R2. A country that fails keeps last month's data.

**Spec:** the app repository's `docs/superpowers/specs/2026-10-10-global-region-data-design.md`, phase 4. This plan adds what measuring showed.

## What measuring showed (2026-10-11)

| | Greece | Austria | Germany (estimate) |
|---|---|---|---|
| Extract | 342 MB | 812 MB | 4.4 GB |
| Build | 3.5 min | 5.7 min | ~30 min |
| Peak memory | — | 1.7 GB | ~9.5 GB |
| Published | 1.5 MB | 1.1 MB | ~6 MB |

A public repository's runner has 16 GB of memory, 14 GB of disk and a 6-hour job limit. Every country Geofabrik serves as one file fits. The United States does not: it is about 11 GB as one file, so it is built from its states' files. Austria at the default level 4 came out as its nine states, with sensible neighbours and its name in Greek taken from OSM.

## Decisions

- **One job per country**, at most 20 at a time, with `fail-fast: false`. A job uploads its country's files and manifest, never the index.
- **The index is written last, by its own job.** It merges this run's entries into the published index. A country whose job failed keeps its entry, and its files from last month are still in the bucket, so a bad build never takes a country out of the app.
- **A country Geofabrik splits** (`geofabrik.toml`: `split = ["us"]`) is built from all its children's files in one job. Places found in two overlapping files are counted once.
- **A country with nothing at its level becomes one region, the whole country**, rather than a failed job. Small states (Malta, Monaco, Liechtenstein) have no admin level 4, and they still deserve their fuel stations.
- **A region crossing the antimeridian is written without bounds.** Its box would span the globe: `regionsNear` would read that country for every position at its latitude, and the picker would offer a map of the whole world. A country's index bounds are the union of its regions that have bounds.
- **Triggers:** `schedule` (03:00 UTC on the 3rd of each month) and `workflow_dispatch`, with an optional `countries` input for a trial run. Never `pull_request` or `pull_request_target`, so no fork ever runs with the secrets. Inputs reach the shell through `env:`, never interpolated into a script.
- **Credentials:** `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ENDPOINT` and `R2_BUCKET` are Actions secrets. They come from a token separate from the maintainer's local `.env`, with Object Read & Write on this bucket only. `upload.py` reads the environment when there is no `.env`.

## Tasks

### Task 1: Several extracts make one country

`build --extract` may be given more than once. Each extract is read in turn. Boundaries are merged by relation id, the first complete one winning. Places are kept once by `(layer, lat, lon, name, kind)`, with coordinates rounded to 7 decimals.

- [ ] Test: two fixtures that overlap, holding the same fuel station, build one country in which that station appears once.
- [ ] Test: a boundary present in both extracts is one region.

### Task 2: A country with nothing at its level is one region

- [ ] Test: with a level at which the fixture has no boundaries, the build yields one region, the country's own polygon, with id `<cc>-<relation>`. Its places are assigned to it.
- [ ] Test: with no country polygon either, the build still fails, with a message naming the country.

### Task 3: Antimeridian

- [ ] Test: a region whose box is wider than 180° has no `bounds` in the manifest.
- [ ] Test: the index bounds come from the other regions. With no bounded region at all, the index entry has no `bounds`.

### Task 4: Upload a country, or the index

- [ ] `upload --country gr` sends `v1/gr/**` only. `upload --index` sends `v1/index.json` only. With neither, it sends everything, as now.
- [ ] Credentials come from `.env` when the file exists, else from the environment.
- [ ] Tests use the existing `FakeBucket`.

### Task 5: Plan from Geofabrik's index

`python -m happyroads_data.plan [--index FILE] [--only gr,at]` prints `matrix=<json>` for `$GITHUB_OUTPUT`. The JSON is a list of `{"country": "gr", "extracts": [url, ...]}`.

- For each ISO code in any feature's `iso3166-1:alpha2`, the extract is the feature listing that code with the fewest codes.
- A code in `split` takes the pbf URLs of the features whose `parent` is that feature.
- Codes are lower-cased and sorted.

Tests, on a trimmed copy of `index-v1.json` in fixtures:

- [ ] Greece maps to its own extract.
- [ ] A code found only in a shared extract maps to the shared one.
- [ ] A split country maps to its children.
- [ ] `--only` narrows the list.

### Task 6: Merge the index

`python -m happyroads_data.index --published URL --entries DIR --out out --version YYYY-MM` reads the live index, ignoring a 404 on the first run. It replaces or adds every `DIR/**/index.json` entry, keeps the rest, sorts by id, and writes `out/v1/index.json`.

- [ ] Test: an entry replaces its country.
- [ ] Test: a country absent from this run is kept.
- [ ] Test: a new country is added.
- [ ] Test: with no published index, the result is just the entries.

### Task 7: The workflow

`.github/workflows/build.yml` has three jobs:

1. **`plan`**, which outputs `matrix` and `version`.
2. **`build`**, a matrix over the countries. For each:
   - curl every extract, with `-fL --retry 3`;
   - build;
   - `upload --country`;
   - upload `out/v1/index.json` as artifact `entry-<cc>`.
3. **`index`**, which runs `if: ${{ !cancelled() && needs.plan.result == 'success' }}`. It downloads every `entry-*` artifact, merges them and runs `upload --index`.

Other settings:
- `permissions: contents: read`.
- Python 3.12, and `pip install osmium shapely boto3`.

Steps:
- [ ] Lint the YAML with `actionlint` if it is available. If not, review it by eye against this list.
- [ ] The maintainer creates the token, adds the four secrets, and runs the workflow with `countries: gr,cy,at`.
- [ ] Then with `de,us`.
- [ ] Then with nothing, which is every country.
- [ ] After the full run: a report of countries with one region, or with more than 150, for `levels.toml`.
