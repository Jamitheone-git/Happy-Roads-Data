"""What each place layer is, in OpenStreetMap's words.

A port of the app's `lib/core/data/osm_layers.dart`. The app used to send
SELECTORS to Overpass and read the answer with its own `osmLayerOf`. Here the
whole extract is read, so `layer_of` has to apply the conditions the selectors
used to apply on the server: which element types, and the `!=` filters.
`tests/test_drift.py` holds SELECTORS to the Dart file.
"""

import re

LAYERS = ['fuel', 'toll', 'camera', 'inspection', 'restArea', 'parking',
          'charging', 'workshop']

SELECTORS = {
    'fuel': ['node["amenity"="fuel"]'],
    'toll': ['node["barrier"="toll_booth"]', 'way["barrier"="toll_booth"]'],
    'camera': ['node["highway"="speed_camera"]'],
    'inspection': ['nwr["amenity"="vehicle_inspection"]'],
    'restArea': ['nwr["highway"="rest_area"]', 'nwr["highway"="services"]'],
    'parking': ['nwr["amenity"="parking"]["access"!="private"]'],
    'charging': ['nwr["amenity"="charging_station"]["motorcar"!="no"]'],
    'workshop': ['nwr["shop"="car_repair"]', 'nwr["shop"="tyres"]'],
}

_ELEMENTS = {'fuel': 'n', 'toll': 'nw', 'camera': 'n'}


def _layer_by_tags(tags):
    if tags.get('amenity') == 'fuel':
        return 'fuel'
    if tags.get('barrier') == 'toll_booth':
        return 'toll'
    if tags.get('highway') == 'speed_camera':
        return 'camera'
    if tags.get('amenity') == 'vehicle_inspection':
        return 'inspection'
    if tags.get('highway') in ('rest_area', 'services'):
        return 'restArea'
    if tags.get('amenity') == 'parking':
        return None if tags.get('access') == 'private' else 'parking'
    if tags.get('amenity') == 'charging_station':
        return None if tags.get('motorcar') == 'no' else 'charging'
    if tags.get('shop') in ('car_repair', 'tyres'):
        return 'workshop'
    return None


def layer_of(tags, element):
    layer = _layer_by_tags(tags)
    if layer is None or element not in _ELEMENTS.get(layer, 'nwr'):
        return None
    return layer


def kind_of(layer, tags):
    if layer == 'restArea':
        return 'services' if tags.get('highway') == 'services' else None
    if layer == 'workshop':
        return 'tyres' if tags.get('shop') == 'tyres' else None
    return None


def attributes_of(layer, tags):
    if layer == 'camera':
        kmh = _kmh(tags.get('maxspeed'))
        return {} if kmh is None else {'maxspeed': kmh}
    if layer == 'parking':
        fee = tags.get('fee')
        return {'fee': True} if fee == 'yes' else {'fee': False} if fee == 'no' else {}
    if layer == 'fuel':
        sold = sorted(key[5:] for key, value in tags.items()
                      if key.startswith('fuel:') and value == 'yes')
        return {'fuels': sold} if sold else {}
    return {}


# A bare number is km/h and "mph" is converted. Anything else (none, GR:urban,
# signals) is a rule rather than a figure, and saying nothing beats a guess.
_SPEED = re.compile(r'^\s*(\d+)\s*(mph)?\s*$')


def _kmh(tag):
    if tag is None:
        return None
    match = _SPEED.match(tag)
    if match is None:
        return None
    figure = int(match.group(1))
    return figure if match.group(2) is None else round(figure * 1.609344)


def encode_entry(lat, lon, name, kind, attributes):
    entry = [round(lat, 7), round(lon, 7), name, kind,
             attributes if attributes else None]
    while len(entry) > 3 and entry[-1] is None:
        entry.pop()
    return entry
