import json

from happyroads_data.index import merge


def _entry(code, version):
    return {'id': code, 'name': code, 'version': version, 'manifest': f'{code}/manifest.json'}


def test_this_runs_entries_replace_their_countries_and_the_rest_are_kept():
    # A country whose job failed this month keeps last month's entry, and its
    # files are still in the bucket: a bad build never takes it out of the app.
    published = {'version': '2026-09', 'countries': [_entry('at', '2026-09'), _entry('gr', '2026-09')]}
    merged = merge(published, [_entry('gr', '2026-10'), _entry('de', '2026-10')], '2026-10')

    assert merged['version'] == '2026-10'
    assert [(c['id'], c['version']) for c in merged['countries']] == [
        ('at', '2026-09'), ('de', '2026-10'), ('gr', '2026-10')]


def test_the_first_run_has_nothing_published_to_keep():
    merged = merge(None, [_entry('gr', '2026-10')], '2026-10')
    assert [c['id'] for c in merged['countries']] == ['gr']


def test_entries_are_read_from_each_jobs_own_index(tmp_path):
    from happyroads_data.index import read_entries
    for code in ('gr', 'at'):
        folder = tmp_path / f'entry-{code}' / 'v1'
        folder.mkdir(parents=True)
        (folder / 'index.json').write_text(
            json.dumps({'version': '2026-10', 'countries': [_entry(code, '2026-10')]}),
            encoding='utf-8')
    assert sorted(e['id'] for e in read_entries(tmp_path)) == ['at', 'gr']
