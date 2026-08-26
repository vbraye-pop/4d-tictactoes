"""Tests for game rules: legality, alternation, win, draw."""

import pytest

from game.board import (
    CROSSES,
    CROSS_MASK_SET,
    FULL_MASK,
    N_CELLS,
    O,
    X,
    Board,
    IllegalMove,
)


def build_board(x_cells, o_cells):
    """Replay a legal alternating game producing the given marks.

    x_cells and o_cells must satisfy len(x) == len(o) or len(x) == len(o) + 1.
    Asserts the game never ends before the final move.
    """
    assert len(x_cells) in (len(o_cells), len(o_cells) + 1)
    b = Board()
    xi = oi = 0
    for _ in range(len(x_cells)):
        b.play(x_cells[xi])
        xi += 1
        if oi < len(o_cells):
            b.play(o_cells[oi])
            oi += 1
    assert not b.is_over or b.move_count() == len(x_cells) + len(o_cells)
    return b


def play_to_winner(b, cell):
    """Play `cell` for whoever moves, then assert the game ended."""
    b.play(cell)
    assert b.is_over


# ---------------------------------------------------------------- alternation

def test_x_moves_first_and_players_alternate():
    b = Board()
    assert b.to_move == X
    b.play(0)
    assert b.to_move == O
    assert b.moves == [0]
    b.play(1)
    assert b.to_move == X
    assert b.move_count() == 2
    assert b.occupant(0) == X
    assert b.occupant(1) == O


# ------------------------------------------------------------------ legality

def test_out_of_range_cells_rejected():
    b = Board()
    for bad in (-1, N_CELLS, N_CELLS + 100):
        with pytest.raises(IllegalMove):
            b.play(bad)
    assert b.move_count() == 0


def test_non_integer_cells_rejected():
    b = Board()
    for bad in (3.0, 3.5, "40", None, [40]):
        with pytest.raises(IllegalMove):
            b.play(bad)
    assert b.move_count() == 0


def test_occupied_cell_rejected():
    b = Board()
    b.play(5)
    with pytest.raises(IllegalMove):
        b.play(5)
    assert b.move_count() == 1


def test_moves_rejected_after_game_over():
    b = Board()
    cross = CROSSES[0]
    # X takes four cells of a cross, O plays elsewhere, X completes.
    x_cells = [cross.line1[1], cross.line1[0], cross.line2[0], cross.line1[2]]
    o_cells = [c for c in range(N_CELLS) if c not in cross.cells][:4]
    for x, o in zip(x_cells, o_cells):
        b.play(x)
        b.play(o)
    b.play(cross.line2[2])
    assert b.winner == X
    with pytest.raises(IllegalMove):
        b.play(0)
    with pytest.raises(IllegalMove):
        b.play(cross.center)
    assert b.move_count() == 9


# ----------------------------------------------------------------------- win

def test_win_detection_and_cross_reference():
    b = Board()
    # plus shape in the w=1 plane centered at (1,1,1,1)
    center = 40  # (1,1,1,1)
    arms = [
        (0, 1, 1, 1),  # 39
        (2, 1, 1, 1),  # 41
        (1, 0, 1, 1),  # 37
        (1, 2, 1, 1),  # 43
    ]
    from game.board import idx_of

    arm_cells = [idx_of(a) for a in arms]
    o_cells = [0, 2, 6, 8]
    for x, o in zip([center, arm_cells[0], arm_cells[1], arm_cells[2]], o_cells):
        b.play(x)
        b.play(o)
    assert not b.is_over
    b.play(arm_cells[3])
    assert b.winner == X
    assert b.winning_cross is not None
    assert b.winning_cross.center == center
    assert set(b.winning_cross.cells) == {center, *arm_cells}
    assert b.to_move == X  # turn no longer advances after a win


def test_every_one_of_the_1548_crosses_is_detected():
    """For each cross: X owns four of its cells, plays the fifth, and the win
    is detected and attributed to exactly that cross."""
    for cross in CROSSES:
        x_cells = list(cross.cells)
        completing = x_cells.pop(0)
        o_cells = [c for c in range(N_CELLS) if c not in cross.cells][:4]
        b = Board()
        for x, o in zip(x_cells, o_cells):
            b.play(x)
            assert not b.is_over
            b.play(o)
            assert not b.is_over
        b.play(completing)
        assert b.winner == X, f"cross {cross} not detected"
        assert b.winning_cross.mask == cross.mask
        assert set(b.winning_cross.cells) == set(cross.cells)


def test_five_cells_that_are_not_a_cross_do_not_win():
    # Take a real cross and move one endpoint off its line: the resulting
    # five-set contains no cross at all.
    cross = next(
        c
        for c in CROSSES
        if c.center == 40
        and c.line1[0] == 13
        and c.line2[0] == 39
    )
    s = set(cross.cells)
    s.discard(67)  # (1,1,1,2)
    s.add(68)  # (1,2,1,2): off both lines
    mask = 0
    for cell in s:
        mask |= 1 << cell
    assert mask not in CROSS_MASK_SET  # precondition: not a cross
    x_cells = sorted(s)
    completing = x_cells.pop(0)
    o_cells = [c for c in range(N_CELLS) if c not in s][:4]
    b = Board()
    for x, o in zip(x_cells, o_cells):
        b.play(x)
        b.play(o)
    b.play(completing)
    assert b.winner is None
    assert b.winning_cross is None
    assert not b.draw
    assert not b.is_over


# ---------------------------------------------------------------------- draw

def _full_split_masks():
    x_mask = 0
    o_mask = 0
    for i in range(N_CELLS):
        if i % 2 == 0:
            x_mask |= 1 << i  # 41 cells
        else:
            o_mask |= 1 << i  # 40 cells
    return x_mask, o_mask


def test_draw_state_when_board_full_without_winner():
    x_mask, o_mask = _full_split_masks()
    b = Board()
    b.x = x_mask
    b.o = o_mask
    assert b.full
    assert b.draw is True
    assert b.winner is None
    assert b.is_over
    assert not b.is_legal(0)  # board full: no move possible


def test_full_board_always_contains_a_monochromatic_cross():
    # The 1548-cross hypergraph is not 2-colorable (verified with an
    # independent SAT and MILP solve during development): every 2-coloring of
    # the 81 cells has a monochromatic cross, so a real game always ends in a
    # win and the draw state above is unreachable by play. This test pins the
    # fact for the specific full split used by the draw test.
    x_mask, o_mask = _full_split_masks()
    mono = [
        c
        for c in CROSSES
        if (c.mask & x_mask) == c.mask or (c.mask & o_mask) == c.mask
    ]
    assert mono


def test_won_full_board_is_not_a_draw():
    b = Board()
    cross = CROSSES[0]
    x_cells = [cross.line1[1], cross.line1[0], cross.line2[0], cross.line1[2]]
    o_cells = [c for c in range(N_CELLS) if c not in cross.cells][:4]
    for x, o in zip(x_cells, o_cells):
        b.play(x)
        b.play(o)
    b.play(cross.line2[2])
    assert b.winner == X
    assert b.draw is False
    assert b.is_over


def test_reset_clears_everything():
    b = Board()
    b.play(0)
    b.play(1)
    b.reset()
    assert b.x == 0 and b.o == 0
    assert b.to_move == X
    assert b.last_move is None
    assert b.winner is None
    assert b.moves == []
    assert not b.is_over
    assert len(b.empty_cells()) == N_CELLS
