"""The files the app downloads, laid out under v1/ so that a later format can
sit beside this one while installed copies of the app keep reading it."""

import gzip
import json

from .layers import LAYERS, encode_entry


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def region_file(layer, places):
    entries = [encode_entry(p.lat, p.lon, p.name, p.kind, p.attributes) for p in places]
    # mtime=0, so the same places give the same bytes, and an upload can skip
    # what has not changed.
    return gzip.compress(_json({layer: entries}).encode('utf-8'), mtime=0)


def _bounds(geometry):
    west, south, east, north = geometry.bounds
    return [round(south, 4), round(west, 4), round(north, 4), round(east, 4)]


def write_country(out, config, regions, assigned, neighbour_ids, version,
                  country_name, country_names):
    base = out / 'v1' / config.id
    for region in regions:
        folder = base / region.id
        folder.mkdir(parents=True, exist_ok=True)
        for layer in LAYERS:
            places = [p for p in assigned[region.id] if p.layer == layer]
            (folder / f'{layer}.json.gz').write_bytes(region_file(layer, places))

    whole = {'id': config.whole_id, 'name': config.whole_name or country_name,
             'names': config.whole_names or country_names,
             'parts': [r.id for r in regions], 'neighborIds': [], 'version': version}
    entries = [{'id': r.id, 'name': r.name, 'names': r.names,
                'neighborIds': neighbour_ids[r.id], 'fileUrl': f'{config.id}/{r.id}',
                'version': version, 'bounds': _bounds(r.geometry)}
               for r in regions]
    manifest = {'id': config.id, 'name': country_name, 'names': country_names,
                'regions': [whole, *entries]}
    (base / 'manifest.json').write_text(_json(manifest), encoding='utf-8')

    south = min(e['bounds'][0] for e in entries)
    west = min(e['bounds'][1] for e in entries)
    north = max(e['bounds'][2] for e in entries)
    east = max(e['bounds'][3] for e in entries)
    return {'id': config.id, 'name': country_name, 'names': country_names,
            'bounds': [south, west, north, east], 'version': version,
            'manifest': f'{config.id}/manifest.json'}


def write_index(out, entries, version):
    path = out / 'v1' / 'index.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json({'version': version, 'countries': entries}), encoding='utf-8')
