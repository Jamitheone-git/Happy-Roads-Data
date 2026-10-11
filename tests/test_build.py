import gzip
import json
from pathlib import Path

import pytest

from happyroads_data.build import main

FIXTURES = Path(__file__).parent / 'fixtures'


def test_a_country_is_built_end_to_end_from_an_extract(tmp_path):
    main(['--country', 'xx', '--extract', str(FIXTURES / 'two_squares.osm'),
          '--out', str(tmp_path), '--version', '2026-10', '--root', str(FIXTURES)])

    manifest = json.loads((tmp_path / 'v1/xx/manifest.json').read_text(encoding='utf-8'))
    ids = [r['id'] for r in manifest['regions']]
    assert ids == ['pretend', 'west', 'xx-501']
    # The alias file names west's neighbours, so the country uses its list
    # and computes none, even for regions the file does not mention.
    assert [r['neighborIds'] for r in manifest['regions'][1:]] == [[], []]
    assert manifest['name'] == 'Χώρα (ψευδ.)'

    west_fuel = json.loads(gzip.decompress((tmp_path / 'v1/xx/west/fuel.json.gz').read_bytes()))
    assert west_fuel == {'fuel': [[0.5, 0.5, 'West Fuel', None, {'fuels': ['diesel']}]]}
    east_camera = json.loads(gzip.decompress((tmp_path / 'v1/xx/xx-501/camera.json.gz').read_bytes()))
    assert east_camera == {'camera': [[0.5, 1.5, None, None, {'maxspeed': 50}]]}
    assert (tmp_path / 'v1/index.json').exists()


def test_without_an_alias_list_neighbours_are_computed(tmp_path):
    root = tmp_path / 'root'
    (root / 'aliases').mkdir(parents=True)
    (root / 'levels.toml').write_text('default = 4\n[levels]\nxx = 6\n', encoding='utf-8')
    main(['--country', 'xx', '--extract', str(FIXTURES / 'two_squares.osm'),
          '--out', str(tmp_path / 'out'), '--version', '2026-10', '--root', str(root)])
    manifest = json.loads((tmp_path / 'out/v1/xx/manifest.json').read_text(encoding='utf-8'))
    by_id = {r['id']: r for r in manifest['regions']}
    assert by_id['xx-500']['neighborIds'] == ['xx-501']
    # With no alias file the country is named by OSM's own level-2 border.
    assert manifest['name'] == 'Χώρα'
    assert manifest['names'] == {'en': 'Country'}


def _layer(out, region, layer):
    path = out / f'v1/xx/{region}/{layer}.json.gz'
    return json.loads(gzip.decompress(path.read_bytes()))[layer]


def test_a_country_split_across_extracts_is_built_from_all_of_them_once(tmp_path):
    # The United States is too big for one file and comes as its states.
    # Neighbouring files overlap at their edges, so whatever sits in both
    # must still be one place, and a border in both one region.
    main(['--country', 'xx',
          '--extract', str(FIXTURES / 'two_squares.osm'),
          '--extract', str(FIXTURES / 'east_square.osm'),
          '--out', str(tmp_path), '--version', '2026-10', '--root', str(FIXTURES)])

    manifest = json.loads((tmp_path / 'v1/xx/manifest.json').read_text(encoding='utf-8'))
    assert [r['id'] for r in manifest['regions']] == ['pretend', 'west', 'xx-501']
    assert len(_layer(tmp_path, 'xx-501', 'camera')) == 1
    assert [p[2] for p in _layer(tmp_path, 'xx-501', 'fuel')] == ['East Fuel']


def test_a_country_with_nothing_at_its_level_is_one_region(tmp_path):
    # Malta, Monaco and Liechtenstein have no admin level 4. They are one
    # region, the whole country, rather than a failed build and no places.
    root = tmp_path / 'root'
    (root / 'aliases').mkdir(parents=True)
    (root / 'levels.toml').write_text('default = 4\n[levels]\nxx = 8\n', encoding='utf-8')
    main(['--country', 'xx', '--extract', str(FIXTURES / 'two_squares.osm'),
          '--out', str(tmp_path / 'out'), '--version', '2026-10', '--root', str(root)])

    manifest = json.loads((tmp_path / 'out/v1/xx/manifest.json').read_text(encoding='utf-8'))
    assert [r['id'] for r in manifest['regions']] == ['xx', 'xx-900']
    assert manifest['regions'][1]['name'] == 'Χώρα'
    assert len(_layer(tmp_path / 'out', 'xx-900', 'fuel')) == 1


def test_with_neither_regions_nor_a_country_border_the_build_says_which_country(tmp_path):
    root = tmp_path / 'root'
    (root / 'aliases').mkdir(parents=True)
    (root / 'levels.toml').write_text('default = 8\n', encoding='utf-8')
    with pytest.raises(SystemExit, match='yy'):
        main(['--country', 'yy', '--extract', str(FIXTURES / 'two_squares.osm'),
              '--out', str(tmp_path / 'out'), '--version', '2026-10', '--root', str(root)])
