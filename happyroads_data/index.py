"""The last step of a monthly run: this run's countries merged into the
published index.
python -m happyroads_data.index --entries DIR --out out --version 2026-10"""

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

from .write import write_index

_PUBLISHED = 'https://happyroads.data.tumeechu.com/v1/index.json'


def merge(published, entries, version):
    """This run's [entries] replace their countries in the [published] index,
    and every other country is kept as it was. A country whose job failed this
    month keeps last month's entry, and its files are still in the bucket, so a
    bad build never takes a country out of the app."""
    countries = {c['id']: c for c in (published or {}).get('countries', [])}
    for entry in entries:
        countries[entry['id']] = entry
    return {'version': version, 'countries': [countries[k] for k in sorted(countries)]}


def read_entries(folder):
    """Each build job's own one-country index.json, wherever the artifacts
    were unpacked under [folder]."""
    entries = []
    for path in sorted(Path(folder).rglob('index.json')):
        entries.extend(json.loads(path.read_text(encoding='utf-8'))['countries'])
    return entries


def _fetch_published(url):
    # Named, because Cloudflare answers 403 to Python's default agent.
    request = urllib.request.Request(
        url, headers={'User-Agent': 'HappyRoads place-data builder'})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # Nothing published yet is the first run, not a failure.
        if error.code == 404:
            return None
        raise


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--entries', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--published', default=_PUBLISHED)
    args = parser.parse_args(argv)

    merged = merge(_fetch_published(args.published), read_entries(args.entries), args.version)
    write_index(Path(args.out), merged['countries'], args.version)
    print(f"index: {len(merged['countries'])} countries")


if __name__ == '__main__':
    main()
