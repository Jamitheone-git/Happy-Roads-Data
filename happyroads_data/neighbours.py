"""Which regions share a land border, for the picker's colour hint.

Two polygons that only touch at a point, or are separated by water, are not
neighbours. Greece once had shores facing each other across a gulf joined as
neighbours, and the picker suggested driving across the sea.
"""

import math

import shapely
from shapely import STRtree

_EARTH_KM = 6371.0088


def km_length(geometry):
    total = 0.0
    for part in shapely.get_parts(geometry):
        if part.geom_type in ('LineString', 'LinearRing'):
            coords = list(part.coords)
            total += sum(_haversine(a, b) for a, b in zip(coords, coords[1:]))
        elif part.geom_type in ('MultiLineString', 'GeometryCollection'):
            total += km_length(part)
    return total


def _haversine(a, b):
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * _EARTH_KM * math.asin(math.sqrt(h))


def neighbours(regions, min_km=1.0):
    result = {region.id: set() for region in regions}
    tree = STRtree([region.geometry for region in regions])

    for i, region in enumerate(regions):
        for j in tree.query(region.geometry, predicate='intersects'):
            j = int(j)
            if j <= i:
                continue
            other = regions[j]
            shared = region.geometry.boundary.intersection(other.geometry.boundary)
            if km_length(shared) >= min_km:
                result[region.id].add(other.id)
                result[other.id].add(region.id)

    return {rid: sorted(ids) for rid, ids in result.items()}


def overlap_neighbours(regions):
    """Neighbours among outlines that overlap rather than meet: Geofabrik cuts
    each part with a margin, so two states' outlines share an area, not a
    line. A corner shared by four (as Arizona, Utah, Colorado and New Mexico
    do) can make a neighbour of a diagonal one; that is only a colour hint in
    the picker."""
    result = {region.id: set() for region in regions}
    tree = STRtree([region.geometry for region in regions])

    for i, region in enumerate(regions):
        for j in tree.query(region.geometry, predicate='intersects'):
            j = int(j)
            if j <= i:
                continue
            if region.geometry.intersection(regions[j].geometry).area > 0:
                result[region.id].add(regions[j].id)
                result[regions[j].id].add(region.id)

    return {rid: sorted(ids) for rid, ids in result.items()}
