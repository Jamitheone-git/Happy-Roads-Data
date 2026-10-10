import gzip
import json

from shapely.geometry import box

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
                     'parts': ['xx-500', 'xx-501'], 'neighborIds': [], 'version': '2026-10'}
    assert west == {'id': 'xx-500', 'name': 'Δύση', 'names': {'en': 'West'},
                    'neighborIds': ['xx-501'], 'fileUrl': 'xx/xx-500', 'version': '2026-10',
                    'bounds': [0.0, 0.0, 1.0, 1.0]}
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
