from pathlib import Path

from happyroads_data.extract import read_extract

FIXTURE = str(Path(__file__).parent / 'fixtures' / 'two_squares.osm')


def _places():
    return read_extract(FIXTURE)[1]


def test_every_administrative_boundary_is_read_with_its_polygon():
    boundaries = {b.relation_id: b for b in read_extract(FIXTURE)[0]}
    assert set(boundaries) == {500, 501, 900}
    assert boundaries[500].tags['name:en'] == 'West'
    assert boundaries[500].geometry.bounds == (0.0, 0.0, 1.0, 1.0)


def test_a_node_is_placed_where_it_is_with_its_name_and_attributes():
    fuel = [p for p in _places() if p.name == 'West Fuel']
    assert len(fuel) == 1
    assert (fuel[0].lat, fuel[0].lon) == (0.5, 0.5)
    assert fuel[0].attributes == {'fuels': ['diesel']}


def test_a_way_is_placed_at_the_centre_of_its_box_as_overpass_out_center_did():
    parking = [p for p in _places() if p.layer == 'parking']
    assert len(parking) == 1
    assert (round(parking[0].lat, 7), round(parking[0].lon, 7)) == (0.3, 1.3)
    assert parking[0].attributes == {'fee': True}


def test_an_unclosed_way_is_still_a_place():
    tolls = [p for p in _places() if p.layer == 'toll']
    assert [(round(t.lat, 7), round(t.lon, 7)) for t in tolls] == [(0.7, 0.2)]


def test_untagged_or_unknown_things_are_not_places():
    assert sorted(p.layer for p in _places()) == ['camera', 'fuel', 'fuel', 'parking', 'toll']


def test_a_subdivisions_names_are_kept_by_its_code_even_unassembled():
    # A state whose border cannot be closed in its own file still has its
    # names on its relation, and a split country's regions take them from it.
    labels = read_extract(FIXTURE).labels
    assert labels['XX-W']['name:en'] == 'West'
