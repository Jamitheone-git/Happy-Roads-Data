import json

from happyroads_data.fetch import fetch


def test_an_ordinary_country_is_its_extracts(tmp_path):
    got = []
    fetch({'country': 'gr', 'name': 'Greece', 'extracts': ['https://x/greece-latest.osm.pbf'],
           'outlines': ['https://x/greece.poly']},
          tmp_path, download=lambda url, path: got.append((url, path.name)))

    assert got == [('https://x/greece-latest.osm.pbf', 'greece-latest.osm.pbf'),
                   ('https://x/greece.poly', 'greece.poly')]
    fetched = json.loads((tmp_path / 'fetched.json').read_text(encoding='utf-8'))
    assert fetched == {'name': 'Greece', 'extracts': [str(tmp_path / 'greece-latest.osm.pbf')],
                       'outlines': [str(tmp_path / 'greece.poly')], 'parts': []}


def test_a_split_country_brings_each_parts_outline_with_it(tmp_path):
    got = []
    fetch({'country': 'us', 'extracts': [], 'parts': [
        {'id': 'us/alabama', 'name': 'Alabama', 'code': 'US-AL',
         'pbf': 'https://x/us/alabama-latest.osm.pbf', 'poly': 'https://x/us/alabama.poly'},
    ]}, tmp_path, download=lambda url, path: got.append(path.name))

    assert got == ['alabama-latest.osm.pbf', 'alabama.poly']
    part = json.loads((tmp_path / 'fetched.json').read_text(encoding='utf-8'))['parts'][0]
    assert part == {'id': 'us/alabama', 'name': 'Alabama', 'code': 'US-AL',
                    'pbf': str(tmp_path / 'alabama-latest.osm.pbf'),
                    'poly': str(tmp_path / 'alabama.poly')}
