"""Build one country: python -m happyroads_data.build --country gr ..."""

import argparse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from .assign import assign
from .config import load_country
from .extract import read_extract
from .neighbours import neighbours
from .regions import LANGUAGES, Region, build_regions, country_boundary
from .write import write_country, write_index

_ROOT = Path(__file__).resolve().parent.parent


def _read_all(paths, jobs=1):
    """Every extract of one country as one. Neighbouring files overlap at
    their edges, so a border in two of them is one region and a place in two
    of them is one place.

    With [jobs] above one the files are read side by side, each in a process
    of its own: the United States is fifty-three files, and one at a time it
    came close to a runner's time limit. Results are taken in the order the
    files were given, so the country comes out the same either way."""
    if jobs > 1 and len(paths) > 1:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            read = list(pool.map(read_extract, paths))
    else:
        read = [read_extract(path) for path in paths]

    boundaries, places = {}, {}
    for found_boundaries, found_places in read:
        for boundary in found_boundaries:
            boundaries.setdefault(boundary.relation_id, boundary)
        for place in found_places:
            key = (place.layer, round(place.lat, 7), round(place.lon, 7),
                   place.name, place.kind)
            places.setdefault(key, place)
    return list(boundaries.values()), list(places.values())


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--country', required=True)
    # Given more than once for a country Geofabrik splits, as it does the
    # United States into its states.
    parser.add_argument('--extract', required=True, action='append')
    parser.add_argument('--out', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--root', default=str(_ROOT))
    parser.add_argument('--jobs', type=int, default=1,
                        help='extracts read at once, for a country of several')
    args = parser.parse_args(argv)

    config = load_country(args.country, Path(args.root))
    boundaries, places = _read_all(args.extract, args.jobs)
    osm_country = country_boundary(boundaries, args.country)
    regions = build_regions(boundaries, config)
    if not regions and osm_country is not None:
        # Malta or Monaco has nothing at level 4. The whole country is then
        # its one region, rather than a failed build and no places at all.
        tags = osm_country.tags
        regions = [Region(f'{args.country}-{osm_country.relation_id}',
                          config.country_name or tags.get('name', args.country.upper()),
                          {lang: tags[f'name:{lang}'] for lang in LANGUAGES
                           if f'name:{lang}' in tags},
                          osm_country.geometry, None)]
    if not regions:
        raise SystemExit(f'{args.country}: no regions at admin_level {config.level}, '
                         'and no country border to fall back on')

    # A country whose alias file lists neighbours uses that list for every
    # region. Greece's was checked by hand, and computing it once joined shores
    # across a gulf.
    if any(alias.neighbours is not None for alias in config.aliases):
        neighbour_ids = {r.id: r.neighbours or [] for r in regions}
    else:
        neighbour_ids = neighbours(regions)

    osm_tags = osm_country.tags if osm_country else {}
    name = config.country_name or osm_tags.get('name', args.country.upper())
    names = config.country_names or {lang: osm_tags[f'name:{lang}'] for lang in LANGUAGES
                                     if f'name:{lang}' in osm_tags}

    out = Path(args.out)
    entry = write_country(out, config, regions, assign(places, regions),
                          neighbour_ids, args.version, name, names)
    write_index(out, [entry], args.version)
    print(f'{args.country}: {len(regions)} regions, {len(places)} places')


if __name__ == '__main__':
    main()
