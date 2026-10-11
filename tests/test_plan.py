import json
from pathlib import Path

from happyroads_data.plan import countries, main

FIXTURES = Path(__file__).parent / 'fixtures'
INDEX = json.loads((FIXTURES / 'geofabrik-index.json').read_text(encoding='utf-8'))
SETTINGS = {'split': ['us'], 'extract': {'vu': 'vanuatu'}}


def _by_country(only=None):
    return {c['country']: c['extracts'] for c in countries(INDEX, SETTINGS, only)}


def test_a_country_with_its_own_extract_is_built_from_it():
    assert _by_country()['gr'] == [
        'https://download.geofabrik.de/europe/greece-latest.osm.pbf']


def test_a_country_found_only_in_a_shared_extract_is_built_from_that():
    # Each takes the shared file, and the build keeps only what lies inside
    # its own border.
    shared = ['https://download.geofabrik.de/asia/israel-and-palestine-latest.osm.pbf']
    assert _by_country()['il'] == shared
    assert _by_country()['ps'] == shared


def test_a_split_country_is_built_from_its_subdivisions_files():
    assert _by_country()['us'] == [
        'https://download.geofabrik.de/north-america/us/alabama-latest.osm.pbf',
        'https://download.geofabrik.de/north-america/us/alaska-latest.osm.pbf',
    ]


def test_a_code_several_extracts_claim_takes_the_one_settled_in_the_settings():
    assert _by_country()['vu'] == [
        'https://download.geofabrik.de/australia-oceania/vanuatu-latest.osm.pbf']


def test_a_code_nobody_has_settled_is_skipped_rather_than_guessed(capsys):
    assert 'qq' not in _by_country()
    assert 'qq' in capsys.readouterr().err


def test_the_countries_are_in_order_and_can_be_narrowed():
    assert list(_by_country()) == ['gr', 'il', 'ps', 'us', 'vu']
    assert list(_by_country(only={'gr', 'us'})) == ['gr', 'us']


def test_it_prints_a_matrix_for_github_actions(capsys, tmp_path):
    main(['--index', str(FIXTURES / 'geofabrik-index.json'), '--only', 'gr,us'])
    line = capsys.readouterr().out.strip()
    assert line.startswith('matrix=')
    assert [c['country'] for c in json.loads(line[len('matrix='):])] == ['gr', 'us']
