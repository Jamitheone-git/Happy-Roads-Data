"""Which countries to build, and from which Geofabrik files:
python -m happyroads_data.plan [--index FILE] [--only gr,at]

Prints `matrix=<json>` for $GITHUB_OUTPUT: a list of
{"country": "gr", "extracts": [url, ...]}, one build job each."""

import argparse
import json
import sys
import tomllib
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_INDEX_URL = 'https://download.geofabrik.de/index-v1-nogeom.json'


def countries(index, settings, only=None):
    features = [f['properties'] for f in index['features']]
    split = set(settings.get('split', []))
    settled = settings.get('extract', {})

    claims = {}
    for feature in features:
        for code in feature.get('iso3166-1:alpha2', []):
            claims.setdefault(code.lower(), []).append(feature)

    result = []
    for code in sorted(claims):
        if only is not None and code not in only:
            continue

        if code in split:
            prefix = f'{code.upper()}-'
            extracts = sorted(
                f['urls']['pbf'] for f in features
                if any(sub.startswith(prefix) for sub in f.get('iso3166-2', [])))
        else:
            extract = _extract_for(code, claims[code], settled)
            if extract is None:
                continue
            extracts = [extract]

        result.append({'country': code, 'extracts': extracts})
    return result


def _extract_for(code, claimants, settled):
    """The one file that is the country: the extract settled for it, else the
    one claiming it with the fewest other countries. A tie is not guessed at.
    Geofabrik tags some Pacific territories with their neighbours' codes, and
    a wrong guess would publish one island's places as another's."""
    if code in settled:
        return next(f['urls']['pbf'] for f in claimants if f['id'] == settled[code])

    fewest = min(len(f['iso3166-1:alpha2']) for f in claimants)
    best = [f for f in claimants if len(f['iso3166-1:alpha2']) == fewest]
    if len(best) > 1:
        names = ', '.join(f['id'] for f in best)
        print(f'::warning::{code}: claimed by {names}; settle it in geofabrik.toml',
              file=sys.stderr)
        return None
    return best[0]['urls']['pbf']


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', help='a saved copy of the index; fetched when absent')
    parser.add_argument('--only', default='', help='comma-separated codes; empty for all')
    parser.add_argument('--settings', default=str(_ROOT / 'geofabrik.toml'))
    args = parser.parse_args(argv)

    if args.index:
        index = json.loads(Path(args.index).read_text(encoding='utf-8'))
    else:
        with urllib.request.urlopen(_INDEX_URL, timeout=60) as response:
            index = json.load(response)

    settings = tomllib.loads(Path(args.settings).read_text(encoding='utf-8'))
    only = {code.strip().lower() for code in args.only.split(',') if code.strip()} or None
    print('matrix=' + json.dumps(countries(index, settings, only), separators=(',', ':')))


if __name__ == '__main__':
    main()
