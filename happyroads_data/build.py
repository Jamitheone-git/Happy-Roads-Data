"""Build one country: python -m happyroads_data.build --country gr ..."""

import argparse
from pathlib import Path

from .assign import assign
from .config import load_country
from .extract import read_extract
from .neighbours import neighbours
from .regions import LANGUAGES, build_regions, country_boundary
from .write import write_country, write_index

_ROOT = Path(__file__).resolve().parent.parent


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--country', required=True)
    parser.add_argument('--extract', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--root', default=str(_ROOT))
    args = parser.parse_args(argv)

    config = load_country(args.country, Path(args.root))
    boundaries, places = read_extract(args.extract)
    regions = build_regions(boundaries, config)
    if not regions:
        raise SystemExit(f'{args.country}: no regions at admin_level {config.level}')

    # A country whose alias file lists neighbours uses that list for every
    # region. Greece's was checked by hand, and computing it once joined shores
    # across a gulf.
    if any(alias.neighbours is not None for alias in config.aliases):
        neighbour_ids = {r.id: r.neighbours or [] for r in regions}
    else:
        neighbour_ids = neighbours(regions)

    osm_country = country_boundary(boundaries, args.country)
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
