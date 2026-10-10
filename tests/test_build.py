import gzip
import json
from pathlib import Path

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
