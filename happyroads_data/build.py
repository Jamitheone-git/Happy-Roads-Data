"""Build one country: python -m happyroads_data.build --country gr ..."""

import argparse
import dataclasses
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from .assign import assign
from .config import load_country
from .extract import read_extract
from .neighbours import km_length, neighbours, overlap_neighbours
from .poly import read_poly
from shapely import STRtree
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points, unary_union
from .regions import (LANGUAGES, Region, build_regions, country_boundary, disambiguate,
                      regions_at)
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
    for found_boundaries, found_places, _ in read:
        for boundary in found_boundaries:
            boundaries.setdefault(boundary.relation_id, boundary)
        for place in found_places:
            key = (place.layer, round(place.lat, 7), round(place.lon, 7),
                   place.name, place.kind)
            places.setdefault(key, place)
    return list(boundaries.values()), list(places.values())


def _read_parts(country, parts, jobs=1):
    """A split country, one region per part, each drawn from the outline
    Geofabrik cut its file with. A state's own OSM border includes its sea
    border, which its file leaves out, so it cannot be closed: read that way,
    twenty-two states and every place in them were lost.

    Returns the boundaries (for the country's own border, if any file holds
    it whole), the places, the regions, and for each place the region of the
    file it came from, which takes it when no outline holds it."""
    paths = [part['pbf'] for part in parts]
    if jobs > 1 and len(paths) > 1:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            read = list(pool.map(read_extract, paths))
    else:
        read = [read_extract(path) for path in paths]

    labels = {}
    for extract in read:
        labels.update(extract.labels)

    regions = []
    for part in parts:
        # Geofabrik names a part by its id; its names are OSM's, on the
        # relation carrying the part's ISO 3166-2 code.
        tags = labels.get(part.get('code'), {})
        regions.append(Region(
            f"{country}-{part['id'].rsplit('/', 1)[-1]}",
            tags.get('name', part['name']),
            {lang: tags[f'name:{lang}'] for lang in LANGUAGES if f'name:{lang}' in tags},
            read_poly(Path(part['poly']).read_text(encoding='utf-8')), None))

    boundaries, places, sources, seen = {}, [], [], set()
    for region, (found_boundaries, found_places, _) in zip(regions, read):
        for boundary in found_boundaries:
            boundaries.setdefault(boundary.relation_id, boundary)
        for place in found_places:
            key = (place.layer, round(place.lat, 7), round(place.lon, 7),
                   place.name, place.kind)
            if key not in seen:
                seen.add(key)
                places.append(place)
                sources.append(region)
    return list(boundaries.values()), places, regions, sources


# How far outside every region a place may be and still go to the nearest:
# far enough to catch a region whose border could not be closed, not so far
# that a wrongly levelled country empties into whatever region it has.
NEAREST_KM = 50

# The levels a country levels.toml does not name tries after its default, and
# how many regions make a level worth taking.
LADDER = (5, 6, 7, 8)
FEWEST, MOST = 2, 150


def _regions_climbing(boundaries, config):
    """The regions at the country's level, or, for a country levels.toml does
    not name and whose default gives fewer than two, at the first lower level
    giving two to 150. Hungary, Ireland and the Baltic states have their
    counties below level 4. Returns the regions and the level they are at."""
    if isinstance(config.level, list):
        return regions_at(boundaries, config, config.level), config.level
    regions = build_regions(boundaries, config)
    if config.level_set or len(regions) >= FEWEST:
        return regions, config.level
    for level in LADDER:
        tried = build_regions(boundaries, dataclasses.replace(config, level=level))
        if FEWEST <= len(tried) <= MOST:
            return tried, level
    return regions, config.level


def _place_the_rest(assigned, places, regions, inside):
    """Places that fell in no region but lie [inside] the country go to the
    nearest region within NEAREST_KM. A region whose border could not be
    closed is missing, and its places would otherwise be lost; next door,
    a driver downloading the neighbour still finds them."""
    placed = {id(place) for found in assigned.values() for place in found}
    tree = STRtree([region.geometry for region in regions])
    for place in places:
        if id(place) in placed:
            continue
        point = Point(place.lon, place.lat)
        if not inside(point):
            continue
        region = regions[int(tree.nearest(point))]
        near, _ = nearest_points(region.geometry, point)
        if km_length(LineString([point, near])) <= NEAREST_KM:
            assigned[region.id].append(place)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--country', required=True)
    # Given more than once for a country Geofabrik splits, as it does the
    # United States into its states.
    parser.add_argument('--extract', action='append', default=[])
    # What `fetch` downloaded: either extracts, or a split country's parts.
    parser.add_argument('--fetched')
    parser.add_argument('--out', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--root', default=str(_ROOT))
    parser.add_argument('--jobs', type=int, default=1,
                        help='extracts read at once, for a country of several')
    args = parser.parse_args(argv)

    config = load_country(args.country, Path(args.root))
    fetched = (json.loads(Path(args.fetched).read_text(encoding='utf-8'))
               if args.fetched else {'extracts': args.extract, 'parts': []})
    parts = fetched.get('parts') or []

    sources = None
    if parts:
        boundaries, places, regions, sources = _read_parts(args.country, parts, args.jobs)
        regions.sort(key=lambda r: r.id)
    else:
        if not fetched['extracts']:
            raise SystemExit('give --extract or --fetched')
        boundaries, places = _read_all(fetched['extracts'], args.jobs)
        regions, level = _regions_climbing(boundaries, config)
        print(f'{args.country}: level {level}')
    osm_country = country_boundary(boundaries, args.country)
    geofabrik_name = fetched.get('name')
    if not regions and osm_country is not None:
        # Malta or Monaco has nothing at level 4. The whole country is then
        # its one region, rather than a failed build and no places at all.
        tags = osm_country.tags
        regions = [Region(f'{args.country}-{osm_country.relation_id}',
                          config.country_name or tags.get('name', args.country.upper()),
                          {lang: tags[f'name:{lang}'] for lang in LANGUAGES
                           if f'name:{lang}' in tags},
                          osm_country.geometry, None)]
    outlines = fetched.get('outlines') or []
    if not regions and outlines:
        # Antarctica or New Caledonia: no regions and no border OSM tags as a
        # country. The outline Geofabrik cut the file with is the one region.
        regions = [Region(f'{args.country}-all',
                          config.country_name or geofabrik_name or args.country.upper(), {},
                          unary_union([read_poly(Path(o).read_text(encoding='utf-8'))
                                       for o in outlines]), None)]
    if not regions:
        raise SystemExit(f'{args.country}: no regions at admin_level {config.level}, '
                         'and no country border to fall back on')

    regions = disambiguate(regions)

    # A country whose alias file lists neighbours uses that list for every
    # region. Greece's was checked by hand, and computing it once joined shores
    # across a gulf.
    if any(alias.neighbours is not None for alias in config.aliases):
        neighbour_ids = {r.id: r.neighbours or [] for r in regions}
    elif parts:
        neighbour_ids = overlap_neighbours(regions)
    else:
        neighbour_ids = neighbours(regions)

    osm_tags = osm_country.tags if osm_country else {}
    name = config.country_name or osm_tags.get('name') or geofabrik_name or args.country.upper()
    names = config.country_names or {lang: osm_tags[f'name:{lang}'] for lang in LANGUAGES
                                     if f'name:{lang}' in osm_tags}

    # A place outside the country's own border, in a file shared with its
    # neighbours, is the neighbour's: neither placed here nor counted lost.
    if osm_country is not None:
        inside = osm_country.geometry.covers
    else:
        inside = lambda point: True  # noqa: E731

    assigned = assign(places, regions)
    if sources is not None:
        placed = {id(place) for found in assigned.values() for place in found}
        for place, source in zip(places, sources):
            if id(place) not in placed:
                assigned[source.id].append(place)
    _place_the_rest(assigned, places, regions, inside)

    placed = {id(place) for found in assigned.values() for place in found}
    ours = [place for place in places
            if id(place) in placed or inside(Point(place.lon, place.lat))]
    dropped = sum(1 for place in ours if id(place) not in placed)
    share = round(100 * dropped / len(ours)) if ours else 0
    print(f'{args.country}: dropped {dropped} of {len(ours)} places ({share}%)')
    if share > 5:
        print(f'::warning::{args.country}: {share}% of places fell in no region')

    out = Path(args.out)
    entry = write_country(out, config, regions, assigned,
                          neighbour_ids, args.version, name, names)
    write_index(out, [entry], args.version)
    print(f'{args.country}: {len(regions)} regions, {len(places)} places')


if __name__ == '__main__':
    main()
