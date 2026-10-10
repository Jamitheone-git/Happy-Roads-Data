"""Each place into the one region whose border holds it."""

from shapely import STRtree
from shapely.geometry import Point


def assign(places, regions):
    result = {region.id: [] for region in regions}
    tree = STRtree([region.geometry for region in regions])

    for place in places:
        hits = tree.query(Point(place.lon, place.lat), predicate='intersects')
        # A place exactly on a shared border touches both. It goes to the
        # lower-indexed region only, so that it is never downloaded twice.
        if len(hits):
            result[regions[int(min(hits))].id].append(place)

    return result
