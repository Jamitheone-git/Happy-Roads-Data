"""Phase 1's gate: does each Greek region hold about what Overpass returns for
the same border today? The counts will not match exactly, because OSM changes
by the minute and the extract is a few hours old. A difference larger than
the tolerance is a bug in the generator until shown otherwise.

    python tools/compare_overpass.py out
"""

import gzip
import json
import sys
import time
import tomllib
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from happyroads_data.layers import LAYERS, SELECTORS, layer_of  # noqa: E402

# The same two servers the app's OverpassHttpClient takes in turn: each has
# busy spells of its own, and one refusing for minutes is common.
ENDPOINTS = ['https://overpass-api.de/api/interpreter',
             'https://maps.mail.ru/osm/tools/overpass/api/interpreter']
ROOT = Path(__file__).resolve().parent.parent


def _query(relations):
    areas = ''.join(f'area({3600000000 + r});' for r in relations)
    statements = '\n'.join(f'  {s}(area.a);' for layer in LAYERS for s in SELECTORS[layer])
    return f'[out:json][timeout:120];\n({areas})->.a;\n(\n{statements}\n);\nout center tags;'


def _ask(query):
    for attempt, pause in enumerate((0, 5, 10, 30, 30, 60, 60, 120, 120, 180)):
        time.sleep(pause)
        request = urllib.request.Request(
            ENDPOINTS[attempt % len(ENDPOINTS)], data=urllib.parse.urlencode({'data': query}).encode(),
            headers={'User-Agent': 'HappyRoads data comparison (one-off)'})
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return json.load(response)
        except Exception as error:  # a busy public server; ask again
            print(f'  retrying after: {error}', flush=True)
    raise SystemExit('Overpass would not answer')


def _overpass_counts(relations):
    counts = dict.fromkeys(LAYERS, 0)
    for element in _ask(_query(relations))['elements']:
        layer = layer_of(element.get('tags', {}), element['type'][0])
        if layer:
            counts[layer] += 1
    return counts


def _our_counts(out, region_id):
    folder = out / 'v1' / 'gr' / region_id
    return {layer: len(json.loads(gzip.decompress((folder / f'{layer}.json.gz').read_bytes()))[layer])
            for layer in LAYERS}


def main(out):
    out = Path(out)
    aliases = tomllib.loads((ROOT / 'aliases' / 'gr.toml').read_text(encoding='utf-8'))['region']
    manifest = json.loads((out / 'v1/gr/manifest.json').read_text(encoding='utf-8'))
    ours_ids = {r['id'] for r in manifest['regions']}
    expected = {a['id'] for a in aliases} | {'greece'}
    if ours_ids != expected:
        raise SystemExit(f'ids differ: missing {expected - ours_ids}, extra {ours_ids - expected}')

    # Overpass's answers are kept, so a run stopped by a server that would
    # not answer picks up where it was rather than asking all seventy again.
    cache_path = out / 'overpass_counts.json'
    cache = json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}

    failures = []
    for alias in aliases:
        theirs = cache.get(alias['id'])
        if theirs is None:
            theirs = _overpass_counts(alias['relations'])
            cache[alias['id']] = theirs
            cache_path.write_text(json.dumps(cache), encoding='utf-8')
            time.sleep(5)
        ours = _our_counts(out, alias['id'])
        for layer in LAYERS:
            if abs(ours[layer] - theirs[layer]) > max(3, theirs[layer] * 0.1):
                failures.append((alias['id'], layer, ours[layer], theirs[layer]))
        print(f"{alias['id']:20} " + ' '.join(f'{l}:{ours[l]}/{theirs[l]}' for l in LAYERS), flush=True)

    for region, layer, ours, theirs in failures:
        print(f'DIFFERS {region} {layer}: ours {ours}, overpass {theirs}')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main(sys.argv[1])
