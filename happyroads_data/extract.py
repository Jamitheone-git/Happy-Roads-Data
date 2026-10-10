"""One pass over an OpenStreetMap extract: the administrative polygons, and
every place belonging to a layer."""

from dataclasses import dataclass

import osmium
import shapely.wkb

from .layers import attributes_of, kind_of, layer_of


@dataclass(frozen=True)
class Place:
    layer: str
    lat: float
    lon: float
    name: str | None
    kind: str | None
    attributes: dict


@dataclass(frozen=True)
class Boundary:
    relation_id: int
    tags: dict
    geometry: object


# Only objects carrying one of these keys reach Python at all. A country
# extract is mostly untagged nodes and buildings, and iterating those in Python
# is what would make a large country take hours.
_KEYS = ('amenity', 'barrier', 'highway', 'shop', 'boundary')


def read_extract(path):
    boundaries, places = [], []
    wkb = osmium.geom.WKBFactory()

    processor = (osmium.FileProcessor(path)
                 .with_locations()
                 .with_areas(osmium.filter.KeyFilter('boundary', 'amenity', 'highway', 'shop'))
                 .with_filter(osmium.filter.KeyFilter(*_KEYS)))

    for obj in processor:
        tags = dict(obj.tags)
        if obj.is_area():
            # Ways are placed from the way itself below. Only a relation needs
            # its assembled polygon, whether it is a border or a place drawn as
            # a multipolygon.
            if obj.from_way():
                continue
            geometry = _polygon(wkb, obj)
            if geometry is None:
                continue
            if tags.get('boundary') == 'administrative':
                boundaries.append(Boundary(obj.orig_id(), tags, geometry))
            else:
                south, west, north, east = _box(geometry)
                _add(places, tags, 'r', (south + north) / 2, (west + east) / 2)
        elif obj.is_node():
            _add(places, tags, 'n', obj.location.lat, obj.location.lon)
        elif obj.is_way():
            points = [(n.lat, n.lon) for n in obj.nodes if n.location.valid()]
            if points:
                lats = [p[0] for p in points]
                lons = [p[1] for p in points]
                _add(places, tags, 'w', (min(lats) + max(lats)) / 2,
                     (min(lons) + max(lons)) / 2)

    return boundaries, places


def _add(places, tags, element, lat, lon):
    layer = layer_of(tags, element)
    if layer is None:
        return
    places.append(Place(layer, lat, lon, tags.get('name'),
                        kind_of(layer, tags), attributes_of(layer, tags)))


def _polygon(wkb, area):
    try:
        return shapely.wkb.loads(wkb.create_multipolygon(area), hex=True)
    except RuntimeError:
        # A broken multipolygon in OSM is somebody's half-finished edit. It is
        # skipped rather than allowed to stop a whole country's build.
        return None


def _box(geometry):
    west, south, east, north = geometry.bounds
    return south, west, north, east
