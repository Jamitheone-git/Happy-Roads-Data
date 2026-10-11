from happyroads_data.poly import read_poly

SQUARE_WITH_HOLE = """somewhere
1
   0 0
   4 0
   4 4
   0 4
   0 0
END
!hole
   1 1
   2 1
   2 2
   1 2
   1 1
END
END
"""


def test_a_poly_file_is_its_rings_less_its_holes():
    # Geofabrik's own outline of each extract, in the osmosis .poly format.
    shape = read_poly(SQUARE_WITH_HOLE)
    assert shape.area == 16 - 1
    assert shape.bounds == (0.0, 0.0, 4.0, 4.0)


def test_several_rings_are_one_shape():
    text = "two\n1\n 0 0\n 1 0\n 1 1\n 0 1\n 0 0\nEND\n2\n 5 5\n 6 5\n 6 6\n 5 6\n 5 5\nEND\nEND\n"
    assert read_poly(text).area == 2
