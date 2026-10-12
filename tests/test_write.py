import gzip
import json

from shapely.geometry import MultiPolygon, Polygon, box

from happyroads_data.config import CountryConfig
from happyroads_data.extract import Place
from happyroads_data.regions import Region
from happyroads_data.write import region_file, write_country, write_index

CONFIG = CountryConfig('xx', 6, [], 'pretend', 'Όλη', {'en': 'All of it'}, None, {})
REGIONS = [Region('xx-500', 'Δύση', {'en': 'West'}, box(0, 0, 1, 1), None),
           Region('xx-501', 'Ανατολή', {}, box(1, 0, 2, 1), None)]
FUEL = Place('fuel', 0.5, 0.5, 'BP', None, {})


def _read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def test_a_region_file_is_one_layer_in_the_apps_format():
    assert json.loads(gzip.decompress(region_file('fuel', [FUEL]))) == {'fuel': [[0.5, 0.5, 'BP']]}


def test_the_same_places_always_give_the_same_bytes():
    assert region_file('fuel', [FUEL]) == region_file('fuel', [FUEL])


def test_every_layer_of_every_region_is_written_even_when_empty(tmp_path):
    write_country(tmp_path, CONFIG, REGIONS, {'xx-500': [FUEL], 'xx-501': []},
                  {'xx-500': ['xx-501'], 'xx-501': ['xx-500']}, '2026-10', 'Χώρα', {})
    assert _read(tmp_path / 'v1/xx/xx-500/fuel.json.gz') == {'fuel': [[0.5, 0.5, 'BP']]}
    # "Asked, and none" has to reach the install as an empty list.
    assert _read(tmp_path / 'v1/xx/xx-501/parking.json.gz') == {'parking': []}
    assert len(list((tmp_path / 'v1/xx/xx-501').iterdir())) == 8


def test_the_manifest_holds_the_regions_and_the_whole_country(tmp_path):
    write_country(tmp_path, CONFIG, REGIONS, {'xx-500': [], 'xx-501': []},
                  {'xx-500': ['xx-501'], 'xx-501': ['xx-500']}, '2026-10', 'Χώρα', {'en': 'Country'})
    manifest = json.loads((tmp_path / 'v1/xx/manifest.json').read_text(encoding='utf-8'))
    assert manifest['id'] == 'xx'
    assert manifest['name'] == 'Χώρα'
    whole, west, east = manifest['regions']
    assert whole == {'id': 'pretend', 'name': 'Όλη', 'names': {'en': 'All of it'},
                     'parts': ['xx-500', 'xx-501'], 'neighborIds': [],
                     'fileUrl': 'xx', 'version': '2026-10'}
    assert west == {'id': 'xx-500', 'name': 'Δύση', 'names': {'en': 'West'},
                    'neighborIds': ['xx-501'], 'fileUrl': 'xx/xx-500', 'version': '2026-10',
                    'bounds': [0.0, 0.0, 1.0, 1.0],
                    'outline': [[[0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0]]]}
    assert east['bounds'] == [0.0, 1.0, 1.0, 2.0]


def test_the_country_returns_its_index_entry_and_the_index_lists_it(tmp_path):
    entry = write_country(tmp_path, CONFIG, REGIONS, {'xx-500': [], 'xx-501': []},
                          {'xx-500': [], 'xx-501': []}, '2026-10', 'Χώρα', {'en': 'Country'})
    assert entry == {'id': 'xx', 'name': 'Χώρα', 'names': {'en': 'Country'},
                     'bounds': [0.0, 0.0, 1.0, 2.0], 'version': '2026-10',
                     'manifest': 'xx/manifest.json'}
    write_index(tmp_path, [entry], '2026-10')
    index = json.loads((tmp_path / 'v1/index.json').read_text(encoding='utf-8'))
    assert index == {'version': '2026-10', 'countries': [entry]}


def test_a_region_across_the_antimeridian_has_no_bounds(tmp_path):
    # Its box would run round the globe: every position at its latitude would
    # seem to be in it, and the picker would offer a map of the whole world.
    chukotka = Region('xx-1', 'Чукотка', {}, box(-180, 62, 180, 72), None)
    entry = write_country(tmp_path, CONFIG, [chukotka, REGIONS[0]],
                          {'xx-1': [], 'xx-500': []}, {'xx-1': [], 'xx-500': []},
                          '2026-10', 'Χώρα', {})
    manifest = json.loads((tmp_path / 'v1/xx/manifest.json').read_text(encoding='utf-8'))

    assert 'bounds' not in manifest['regions'][1]
    # The country's own box is the regions that have one.
    assert entry['bounds'] == [0.0, 0.0, 1.0, 1.0]


def test_a_country_with_no_bounded_region_has_no_bounds_in_the_index(tmp_path):
    fiji = Region('xx-2', 'Fiji', {}, box(-180, -21, 180, -12), None)
    entry = write_country(tmp_path, CONFIG, [fiji], {'xx-2': []}, {'xx-2': []},
                          '2026-10', 'Fiji', {})
    assert 'bounds' not in entry


def _manifest(tmp_path, regions):
    write_country(tmp_path, CONFIG, regions, {r.id: [] for r in regions},
                  {r.id: [] for r in regions}, '2026-10', 'Χώρα', {})
    return json.loads((tmp_path / 'v1/xx/manifest.json').read_text(encoding='utf-8'))


def test_an_outline_is_rings_of_latitude_then_longitude_not_closed(tmp_path):
    triangle = Region('xx-7', 'Τρίγωνο', {},
                      Polygon([(21.0, 38.0), (22.0, 38.0), (21.0, 39.0)]), None)
    ring = _manifest(tmp_path, [triangle])['regions'][1]['outline'][0][0]
    assert len(ring) == 6
    points = {(ring[i], ring[i + 1]) for i in range(0, 6, 2)}
    assert points == {(38.0, 21.0), (38.0, 22.0), (39.0, 21.0)}


def test_an_outline_is_rounded_to_three_decimals(tmp_path):
    odd = Region('xx-8', 'Odd', {}, box(21.00049, 38.00049, 22.12345, 39.98765), None)
    ring = _manifest(tmp_path, [odd])['regions'][1]['outline'][0][0]
    assert all(v == round(v, 3) for v in ring)


def test_an_outline_keeps_its_holes(tmp_path):
    holed = Polygon(box(0, 0, 4, 4).exterior.coords, [box(1, 1, 3, 3).exterior.coords])
    outline = _manifest(tmp_path, [Region('xx-9', 'Holed', {}, holed, None)])['regions'][1]['outline']
    assert len(outline) == 1 and len(outline[0]) == 2


def test_islands_are_polygons_of_their_own(tmp_path):
    islands = MultiPolygon([box(0, 0, 1, 1), box(3, 3, 4, 4)])
    outline = _manifest(tmp_path, [Region('xx-10', 'Islands', {}, islands, None)])['regions'][1]['outline']
    assert len(outline) == 2


def test_a_region_across_the_antimeridian_still_has_an_outline(tmp_path):
    # OSM splits it at ±180, so its box runs round the globe and is dropped,
    # but a point-in-polygon test on the two halves is exact.
    halves = MultiPolygon([box(170, 62, 180, 72), box(-180, 62, -170, 72)])
    entry = _manifest(tmp_path, [Region('xx-11', 'Чукотка', {}, halves, None)])['regions'][1]
    assert 'bounds' not in entry
    assert len(entry['outline']) == 2


def test_the_whole_country_has_no_outline(tmp_path):
    assert 'outline' not in _manifest(tmp_path, REGIONS)['regions'][0]
