from happyroads_data.layers import (
    LAYERS, attributes_of, encode_entry, kind_of, layer_of,
)


def test_the_layers_are_the_apps_and_in_its_order():
    assert LAYERS == ['fuel', 'toll', 'camera', 'inspection', 'restArea',
                      'parking', 'charging', 'workshop']


def test_a_fuel_station_is_fuel_only_as_a_node():
    # Overpass was asked for node["amenity"="fuel"] alone, so a station drawn
    # as a forecourt outline was never in the app's data either.
    assert layer_of({'amenity': 'fuel'}, 'n') == 'fuel'
    assert layer_of({'amenity': 'fuel'}, 'w') is None


def test_a_toll_booth_may_be_a_way_but_never_a_relation():
    assert layer_of({'barrier': 'toll_booth'}, 'w') == 'toll'
    assert layer_of({'barrier': 'toll_booth'}, 'r') is None


def test_private_parking_and_chargers_closed_to_cars_are_left_out():
    assert layer_of({'amenity': 'parking'}, 'w') == 'parking'
    assert layer_of({'amenity': 'parking', 'access': 'private'}, 'w') is None
    assert layer_of({'amenity': 'charging_station'}, 'n') == 'charging'
    assert layer_of({'amenity': 'charging_station', 'motorcar': 'no'}, 'n') is None


def test_services_and_tyre_shops_are_the_second_kind_of_their_layer():
    assert layer_of({'highway': 'services'}, 'r') == 'restArea'
    assert kind_of('restArea', {'highway': 'services'}) == 'services'
    assert kind_of('restArea', {'highway': 'rest_area'}) is None
    assert kind_of('workshop', {'shop': 'tyres'}) == 'tyres'
    assert kind_of('workshop', {'shop': 'car_repair'}) is None


def test_anything_else_is_no_layer():
    assert layer_of({'amenity': 'cafe'}, 'n') is None


def test_a_camera_keeps_its_limit_in_kmh_and_drops_a_rule():
    assert attributes_of('camera', {'maxspeed': '50'}) == {'maxspeed': 50}
    assert attributes_of('camera', {'maxspeed': '30 mph'}) == {'maxspeed': 48}
    assert attributes_of('camera', {'maxspeed': 'GR:urban'}) == {}


def test_a_station_lists_what_it_sells_in_a_fixed_order():
    tags = {'fuel:lpg': 'yes', 'fuel:diesel': 'yes', 'fuel:octane_100': 'no'}
    assert attributes_of('fuel', tags) == {'fuels': ['diesel', 'lpg']}
    assert attributes_of('fuel', {}) == {}


def test_parking_says_whether_it_charges_only_when_it_is_known():
    assert attributes_of('parking', {'fee': 'yes'}) == {'fee': True}
    assert attributes_of('parking', {'fee': 'no'}) == {'fee': False}
    assert attributes_of('parking', {}) == {}


def test_an_entry_drops_trailing_blanks_but_keeps_the_name_slot():
    assert encode_entry(38.1, 23.2, None, None, {}) == [38.1, 23.2, None]
    assert encode_entry(38.1, 23.2, 'BP', None, {}) == [38.1, 23.2, 'BP']
    assert encode_entry(38.1, 23.2, None, 'tyres', {}) == [38.1, 23.2, None, 'tyres']
    assert encode_entry(38.1, 23.2, 'X', None, {'fee': True}) == [38.1, 23.2, 'X', None, {'fee': True}]


def test_an_entry_rounds_to_osms_own_precision():
    assert encode_entry(38.123456789, 23.1, None, None, {})[0] == 38.1234568
