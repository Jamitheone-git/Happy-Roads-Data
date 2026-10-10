from shapely.geometry import LineString, box

from happyroads_data.neighbours import km_length, neighbours
from happyroads_data.regions import Region


def _region(rid, geometry):
    return Region(rid, rid, {}, geometry, None)


def test_a_degree_of_latitude_is_about_111_km():
    assert 110 < km_length(LineString([(0, 0), (0, 1)])) < 112


def test_regions_sharing_a_border_are_neighbours_both_ways():
    result = neighbours([_region('a', box(0, 0, 0.1, 0.1)),
                         _region('b', box(0.1, 0, 0.2, 0.1))])
    assert result == {'a': ['b'], 'b': ['a']}


def test_regions_meeting_at_a_corner_are_not():
    result = neighbours([_region('a', box(0, 0, 0.1, 0.1)),
                         _region('b', box(0.1, 0.1, 0.2, 0.2))])
    assert result == {'a': [], 'b': []}


def test_regions_across_water_are_not():
    result = neighbours([_region('a', box(0, 0, 0.1, 0.1)),
                         _region('b', box(0.2, 0, 0.3, 0.1))])
    assert result == {'a': [], 'b': []}


def test_a_border_shorter_than_a_kilometre_does_not_count():
    # 0.005 degrees of latitude is about 550 m: a sliver where two borders
    # brush, not a border a driver crosses.
    result = neighbours([_region('a', box(0, 0, 0.1, 0.005)),
                         _region('b', box(0.1, 0, 0.2, 0.005))])
    assert result == {'a': [], 'b': []}
