"""Geofabrik's outline of an extract, in the osmosis .poly format: a name,
then rings of "lon lat" lines each closed by END, a ring whose name starts
with "!" being a hole, and a last END."""

from shapely.geometry import Polygon
from shapely.ops import unary_union


def read_poly(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    outers, holes = [], []
    ring, is_hole = None, False

    for line in lines[1:]:
        if ring is None:
            if line == 'END':
                break
            ring, is_hole = [], line.startswith('!')
        elif line == 'END':
            (holes if is_hole else outers).append(Polygon(ring))
            ring = None
        else:
            lon, lat = line.split()[:2]
            ring.append((float(lon), float(lat)))

    shape = unary_union(outers)
    if holes:
        shape = shape.difference(unary_union(holes))
    return shape
