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
    # OSM splits a region across the antimeridian at ±180, so its box runs
    # round the globe. No box beats that one: every position at its latitude
    # would seem to be in it, and the picker would offer the whole world's map.
    if east - west > 180:
        return None
    return [round(south, 4), round(west, 4), round(north, 4), round(east, 4)]


# About two hundred metres. Omonia is two kilometres from the West Athens
# border; finer than this doubles the manifest for nothing a driver can see.
OUTLINE_TOLERANCE = 0.002


def _ring(ring):
    # Latitude first, as bounds is. The closing point repeats the first and is
    # left for the reader to assume.
    return [v for lon, lat in list(ring.coords)[:-1] for v in (round(lat, 3), round(lon, 3))]


def _outline(geometry):
    """The region's border for telling where a position is: polygons of rings,
    outer first. Written even across the antimeridian, where the box is not,
    because OSM splits such a region at ±180 and a test on the halves is exact.
    None when simplifying leaves nothing that encloses anything."""
    shape = geometry.simplify(OUTLINE_TOLERANCE, preserve_topology=True)
    parts = [shape] if shape.geom_type == 'Polygon' else [
        g for g in getattr(shape, 'geoms', []) if g.geom_type == 'Polygon']
    polygons = []
    for part in parts:
        if part.is_empty:
            continue
        outer = _ring(part.exterior)
        if len(outer) < 6:
            continue
        polygons.append([outer, *[r for r in map(_ring, part.interiors) if len(r) >= 6]])
    return polygons or None


def write_country(out, config, regions, assigned, neighbour_ids, version,
                  country_name, country_names):
    base = out / 'v1' / config.id
    for region in regions:
        folder = base / region.id
        folder.mkdir(parents=True, exist_ok=True)
        for layer in LAYERS:
            places = [p for p in assigned[region.id] if p.layer == layer]
            (folder / f'{layer}.json.gz').write_bytes(region_file(layer, places))

    # The whole country has no files of its own: its parts are its places.
    # Naming the country's folder is enough for the app to find each part at
    # <folder>/<partId>, by the same layout every region already follows.
    whole = {'id': config.whole_id, 'name': config.whole_name or country_name,
             'names': config.whole_names or country_names,
             'parts': [r.id for r in regions], 'neighborIds': [],
             'fileUrl': config.id, 'version': version}
    entries = []
    for r in regions:
        entry = {'id': r.id, 'name': r.name, 'names': r.names,
                 'neighborIds': neighbour_ids[r.id], 'fileUrl': f'{config.id}/{r.id}',
                 'version': version}
        bounds = _bounds(r.geometry)
        if bounds is not None:
            entry['bounds'] = bounds
        outline = _outline(r.geometry)
        if outline is not None:
            entry['outline'] = outline
        entries.append(entry)
    manifest = {'id': config.id, 'name': country_name, 'names': country_names,
                'regions': [whole, *entries]}
    (base / 'manifest.json').write_text(_json(manifest), encoding='utf-8')

    index_entry = {'id': config.id, 'name': country_name, 'names': country_names,
                   'version': version, 'manifest': f'{config.id}/manifest.json'}
    boxes = [e['bounds'] for e in entries if 'bounds' in e]
    if boxes:
        index_entry['bounds'] = [min(b[0] for b in boxes), min(b[1] for b in boxes),
                                 max(b[2] for b in boxes), max(b[3] for b in boxes)]
    return index_entry


def write_index(out, entries, version):
    path = out / 'v1' / 'index.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json({'version': version, 'countries': entries}), encoding='utf-8')
