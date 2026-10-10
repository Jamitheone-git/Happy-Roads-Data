from shapely.geometry import box

from happyroads_data.assign import assign
from happyroads_data.extract import Place
from happyroads_data.regions import Region


def _place(lat, lon):
    return Place('fuel', lat, lon, None, None, {})


REGIONS = [Region('a', 'A', {}, box(0, 0, 1, 1), None),
           Region('b', 'B', {}, box(1, 0, 2, 1), None)]


def test_a_place_goes_to_the_region_it_is_in():
    result = assign([_place(0.5, 0.5), _place(0.5, 1.5)], REGIONS)
    assert [len(result['a']), len(result['b'])] == [1, 1]


def test_a_place_on_a_shared_border_is_counted_once():
    result = assign([_place(0.5, 1.0)], REGIONS)
    assert len(result['a']) + len(result['b']) == 1


def test_a_place_in_no_region_is_dropped_and_an_empty_region_is_still_there():
    result = assign([_place(5, 5)], REGIONS)
    assert result == {'a': [], 'b': []}
