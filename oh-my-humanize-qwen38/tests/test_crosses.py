"""Tests for winning-cross geometry on the 3x3x3x3 board."""

from itertools import combinations

from game.board import CROSSES, CROSS_MASK_SET, DIRECTIONS, N_CELLS, coord_of

CENTER = next(i for i in range(N_CELLS) if coord_of(i) == (1, 1, 1, 1))


def test_exactly_1548_distinct_crosses():
    assert len(CROSSES) == 1548
    assert len({c.mask for c in CROSSES}) == 1548
    assert CROSS_MASK_SET == {c.mask for c in CROSSES}


def test_40_undirected_directions():
    # 3^4 - 1 = 80 nonzero vectors, paired by negation -> 40 directions.
    assert len(DIRECTIONS) == 40
    for d in DIRECTIONS:
        assert any(d)
        assert all(e in (-1, 0, 1) for e in d)
        first = next(e for e in d if e != 0)
        assert first == 1  # canonical form


def test_every_cross_has_valid_shape():
    for c in CROSSES:
        cells = set(c.cells)
        assert len(cells) == 5
        assert all(0 <= cell < N_CELLS for cell in cells)
        assert c.mask & (1 << c.center)
        for line in (c.line1, c.line2):
            a, mid, b = line
            assert mid == c.center
            assert len({a, mid, b}) == 3
            for i in range(4):
                # middle cell is the coordinate midpoint: the line is straight
                assert 2 * coord_of(mid)[i] == coord_of(a)[i] + coord_of(b)[i]
        # the two lines share only the center and point in different directions
        assert set(c.line1) & set(c.line2) == {c.center}
        d1 = tuple(coord_of(c.line1[2])[i] - coord_of(c.line1[0])[i] for i in range(4))
        d2 = tuple(coord_of(c.line2[2])[i] - coord_of(c.line2[0])[i] for i in range(4))
        assert d2 != d1 and d2 != tuple(-e for e in d1)
        # mask equals the union of the five cells
        union = 0
        for cell in cells:
            union |= 1 << cell
        assert c.mask == union


def test_2d_plane_matches_six_shapes():
    # Restricted to one 2D 3x3 plane the rule yields exactly six crosses:
    # the plus, the X, and four mixed line-plus-diagonal shapes, all through
    # the plane's center.
    in_plane = [
        c
        for c in CROSSES
        if all(coord_of(cell)[2] == 1 and coord_of(cell)[3] == 1 for cell in c.cells)
    ]
    assert len(in_plane) == 6
    assert all(c.center == CENTER for c in in_plane)


def test_cross_count_by_center_class():
    # A cross centered at c pairs the lines through c; a line fits only along
    # coordinates where c has coordinate 1, giving (3^k - 1) / 2 lines for k
    # such coordinates. Summing C(lines, 2) over the 81 centers gives 1548.
    total = 0
    for center in range(N_CELLS):
        k = sum(1 for e in coord_of(center) if e == 1)
        lines = (3**k - 1) // 2
        total += len(list(combinations(range(lines), 2))) if lines >= 2 else 0
    assert total == len(CROSSES) == 1548
