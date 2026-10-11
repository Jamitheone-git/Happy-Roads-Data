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


def _layer(out, region, layer, country='xx'):
    path = out / f'v1/{country}/{region}/{layer}.json.gz'
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
    (root / 'levels.toml').write_text('default = 8\n[levels]\nyy = 8\n', encoding='utf-8')
    with pytest.raises(SystemExit, match='yy'):
        main(['--country', 'yy', '--extract', str(FIXTURES / 'two_squares.osm'),
              '--out', str(tmp_path / 'out'), '--version', '2026-10', '--root', str(root)])


def test_extracts_read_side_by_side_give_the_same_country(tmp_path):
    # The United States is fifty-three files; a runner has four cores, and
    # reading them one at a time came close to the job's time limit.
    def build(out, *jobs):
        main(['--country', 'xx',
              '--extract', str(FIXTURES / 'two_squares.osm'),
              '--extract', str(FIXTURES / 'east_square.osm'),
              '--out', str(out), '--version', '2026-10', '--root', str(FIXTURES), *jobs])

    build(tmp_path / 'one')
    build(tmp_path / 'two', '--jobs', '2')

    files = sorted(p.relative_to(tmp_path / 'one') for p in (tmp_path / 'one').rglob('*') if p.is_file())
    assert files
    for path in files:
        assert (tmp_path / 'one' / path).read_bytes() == (tmp_path / 'two' / path).read_bytes(), path


def _parts(tmp_path):
    parts = tmp_path / 'fetched.json'
    parts.write_text(json.dumps({'parts': [
        {'id': 'xx/west-side', 'name': 'xx/west-side', 'code': 'XX-W',
         'pbf': str(FIXTURES / 'two_squares.osm'), 'poly': str(FIXTURES / 'west.poly')},
        {'id': 'xx/east-side', 'name': 'xx/east-side', 'code': 'XX-E',
         'pbf': str(FIXTURES / 'east_square.osm'), 'poly': str(FIXTURES / 'east.poly')},
    ]}), encoding='utf-8')
    return parts


def test_a_split_country_takes_its_regions_from_geofabriks_own_outlines(tmp_path):
    # A state's OSM border includes its sea border, which its Geofabrik file
    # leaves out; it cannot be closed, and the state and all its places were
    # lost. The outline Geofabrik cut the file with is the state, whole.
    root = tmp_path / 'root'
    (root / 'aliases').mkdir(parents=True)
    (root / 'levels.toml').write_text('default = 4\n', encoding='utf-8')
    main(['--country', 'xx', '--fetched', str(_parts(tmp_path)),
          '--out', str(tmp_path / 'out'), '--version', '2026-10', '--root', str(root)])

    manifest = json.loads((tmp_path / 'out/v1/xx/manifest.json').read_text(encoding='utf-8'))
    regions = {r['id']: r for r in manifest['regions'][1:]}
    assert sorted(regions) == ['xx-east-side', 'xx-west-side']
    # Geofabrik names a part by its id; the names are OSM's, found by the
    # part's ISO 3166-2 code on its relation even where the border cannot be
    # closed.
    assert regions['xx-west-side']['name'] == 'Δύση'
    assert regions['xx-west-side']['names'] == {'en': 'West', 'el': 'Δύση'}
    assert regions['xx-east-side']['name'] == 'Ανατολή'
    assert regions['xx-west-side']['neighborIds'] == ['xx-east-side']

    out = tmp_path / 'out'
    # The unnamed station at (5, 5) lies in no outline; it came in the west
    # file, so it stays with the west, as a place in Geofabrik's margin would.
    assert [p[2] for p in _layer(out, 'xx-west-side', 'fuel')] == ['West Fuel', None]
    assert [p[2] for p in _layer(out, 'xx-east-side', 'fuel')] == ['East Fuel']
    # The camera is in both files and in the east outline: once, in the east.
    assert len(_layer(out, 'xx-east-side', 'camera')) == 1
    assert _layer(out, 'xx-west-side', 'camera') == []


def test_the_build_says_how_many_places_found_no_region(tmp_path, capsys):
    # The check that found the United States losing twenty-two states: a
    # country whose places mostly fall outside its regions is visibly wrong.
    main(['--country', 'xx', '--extract', str(FIXTURES / 'two_squares.osm'),
          '--out', str(tmp_path), '--version', '2026-10', '--root', str(FIXTURES)])
    # The station at (5, 5) is outside the country's border too: in a shared
    # extract it is a neighbour's, not lost, and is not counted.
    assert 'dropped 0 of 4 places (0%)' in capsys.readouterr().out


def _bare_root(tmp_path, levels='default = 4\n'):
    root = tmp_path / 'root'
    (root / 'aliases').mkdir(parents=True)
    (root / 'levels.toml').write_text(levels, encoding='utf-8')
    return root


def test_a_place_just_outside_every_region_goes_to_the_nearest(tmp_path, capsys):
    # A region whose border cannot be closed is missing, and its places would
    # be lost; within 50 km of another region of the same country they go
    # there instead, where a driver downloading the neighbour finds them.
    main(['--country', 'xx', '--extract', str(FIXTURES / 'near_miss.osm'),
          '--out', str(tmp_path / 'out'), '--version', '2026-10',
          '--root', str(_bare_root(tmp_path, 'default = 4\n[levels]\nxx = 6\n'))])
    names = [p[2] for p in _layer(tmp_path / 'out', 'xx-501', 'fuel')]
    assert names == ['Near Fuel']
    assert 'dropped 0 of 5 places (0%)' in capsys.readouterr().out


def test_a_country_with_no_level_of_its_own_climbs_until_it_has_regions(tmp_path, capsys):
    # Hungary, Ireland and the Baltic states have nothing at level 4 but their
    # counties lower down. A country levels.toml does not name tries 5, 6, 7
    # and 8 in turn, and takes the first giving two to 150 regions.
    main(['--country', 'xx', '--extract', str(FIXTURES / 'two_squares.osm'),
          '--out', str(tmp_path / 'out'), '--version', '2026-10',
          '--root', str(_bare_root(tmp_path))])
    manifest = json.loads((tmp_path / 'out/v1/xx/manifest.json').read_text(encoding='utf-8'))
    assert [r['id'] for r in manifest['regions']] == ['xx', 'xx-500', 'xx-501']
    assert 'xx: level 6' in capsys.readouterr().out


def test_a_country_with_neither_regions_nor_border_is_its_extracts_outline(tmp_path):
    # Antarctica and New Caledonia have no border OSM tags as a country. The
    # outline Geofabrik cut the file with is then the one region, named as
    # Geofabrik names the country.
    fetched = tmp_path / 'fetched.json'
    fetched.write_text(json.dumps({
        'name': 'Yonder', 'extracts': [str(FIXTURES / 'two_squares.osm')],
        'outlines': [str(FIXTURES / 'west.poly')], 'parts': []}), encoding='utf-8')
    main(['--country', 'yy', '--fetched', str(fetched),
          '--out', str(tmp_path / 'out'), '--version', '2026-10',
          '--root', str(_bare_root(tmp_path, 'default = 9\n[levels]\nyy = 9\n'))])
    manifest = json.loads((tmp_path / 'out/v1/yy/manifest.json').read_text(encoding='utf-8'))
    assert manifest['name'] == 'Yonder'
    assert [(r['id'], r['name']) for r in manifest['regions'][1:]] == [('yy-all', 'Yonder')]
    assert [p[2] for p in _layer(tmp_path / 'out', 'yy-all', 'fuel', 'yy')] == ['West Fuel']
