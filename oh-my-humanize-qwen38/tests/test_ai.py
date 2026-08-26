"""Tests for the AI: wins, blocks, endgame optimality, determinism."""

import pytest

from game import O, X
from game.ai import INF, _search, _threats, _win_cells, ai_move
from game.board import FULL_MASK, Board, coord_of, idx_of


def mask_of(cells):
    m = 0
    for c in cells:
        m |= 1 << c
    return m


def replay(x_cells, o_cells):
    """Replay an alternating game; returns the Board with O or X to move."""
    assert len(x_cells) in (len(o_cells), len(o_cells) + 1)
    b = Board()
    xi = 0
    for o in o_cells:
        b.play(x_cells[xi])
        xi += 1
        b.play(o)
    if xi < len(x_cells):
        b.play(x_cells[xi])
    assert b.move_count() == len(x_cells) + len(o_cells)
    return b


CROSS = idx_of((1, 1, 1, 1))  # 40
ARM_X1 = idx_of((0, 1, 1, 1))  # 39
ARM_X2 = idx_of((2, 1, 1, 1))  # 41
ARM_Y1 = idx_of((1, 0, 1, 1))  # 37
ARM_Y2 = idx_of((1, 2, 1, 1))  # 43
# cross K = {40, 39, 41, 37, 43}: X-axis line plus Y-axis line through 40
K = {CROSS, ARM_X1, ARM_X2, ARM_Y1, ARM_Y2}

AWAY_X = [idx_of((0, 0, 0, 0)), idx_of((2, 0, 0, 0)), idx_of((0, 2, 0, 0)),
          idx_of((2, 2, 0, 0)), idx_of((0, 0, 2, 0))]
AWAY_O = [idx_of((0, 0, 0, 0)), idx_of((2, 0, 0, 0)), idx_of((0, 2, 0, 0)),
          idx_of((2, 2, 0, 0))]


# ------------------------------------------------------------------ immediate

def test_ai_takes_immediate_win():
    # O owns four cells of cross K; O to move must take the fifth.
    b = replay([AWAY_X[0], AWAY_X[1], AWAY_X[2], AWAY_X[3], AWAY_X[4]],
               [CROSS, ARM_X1, ARM_X2, ARM_Y1])
    assert b.to_move == O
    assert not b.is_over
    assert _win_cells(b.o, FULL_MASK ^ (b.x | b.o)) & (1 << ARM_Y2)
    cell, val = ai_move(b.x, b.o, O)
    assert cell == ARM_Y2
    assert val == 1
    b.play(cell)
    assert b.winner == O


def test_ai_blocks_immediate_threat():
    # X owns four cells of K with ARM_Y2 open; O to move, O has no win.
    b = replay([CROSS, ARM_X1, ARM_X2, ARM_Y1], AWAY_O[:3])
    assert b.to_move == O
    threats = _threats(b.x, b.x | b.o)
    assert threats == 1 << ARM_Y2  # exactly one X threat
    assert _win_cells(b.o, FULL_MASK ^ (b.x | b.o)) == 0  # O has no win
    cell, _val = ai_move(b.x, b.o, O)
    assert cell == ARM_Y2  # the only move that does not lose at once
    # any other move lets X complete the cross
    for other in [c for c in b.empty_cells() if c != ARM_Y2][:6]:
        x2 = b.x
        o2 = b.o | (1 << other)
        assert _win_cells(x2, FULL_MASK ^ (x2 | o2)) & (1 << ARM_Y2)
    b.play(cell)
    assert _win_cells(b.x, FULL_MASK ^ (b.x | b.o)) == 0  # threat gone


# ------------------------------------------------- endgame optimality (search)
#
# Dense endgame fixtures, built offline with the engine itself: each is a
# legal, non-terminal position (replayed below) with a structure the AI must
# prove. 4D endgames are saturated with 4-of-5 positions, so every deep
# position is decided by forced lines; the exact search (or the forced-line
# shortcut, which the search mirrors) must return a provable +1 or -1.

DENSE_WIN_X = [
    0, 1, 2, 5, 6, 10, 11, 12, 15, 16, 19, 21, 24, 25, 26, 28, 29, 30, 32, 33,
    34, 35, 44, 46, 50, 53, 54, 57, 65, 68, 70, 71, 72, 73, 77,
]
DENSE_WIN_O = [
    3, 7, 8, 9, 14, 17, 18, 20, 22, 23, 27, 31, 37, 38, 41, 42, 43, 45, 48, 51,
    52, 55, 56, 58, 60, 62, 63, 64, 66, 67, 69, 75, 76, 80,
]
# O to move, O holds twelve immediate winning cells (69 filled, 12 empty).

DENSE_LOSS_X = [
    3, 7, 10, 12, 13, 15, 17, 20, 22, 25, 28, 30, 32, 35, 37, 38, 39, 40, 41,
    44, 49, 51, 53, 54, 56, 59, 66, 69, 72, 74, 76, 79,
]
DENSE_LOSS_O = [
    0, 1, 2, 5, 6, 9, 11, 14, 16, 18, 19, 21, 24, 27, 29, 31, 34, 36, 42, 46,
    47, 50, 52, 55, 58, 64, 65, 68, 71, 75, 77,
]
# O to move, X holds two (of several) open threats, O has no win.


def dense_position(x_cells, o_cells):
    b = replay(x_cells, o_cells)
    assert not b.is_over
    return b


def test_dense_endgame_win_is_proven():
    b = dense_position(DENSE_WIN_X, DENSE_WIN_O)
    assert b.to_move == O
    free = FULL_MASK ^ (b.x | b.o)
    wins = _win_cells(b.o, free)
    assert wins.bit_count() >= 2  # O is winning in the open
    cell, val = ai_move(b.x, b.o, O)
    assert val == 1
    assert (1 << cell) & wins  # takes one of the winning cells
    # taking the move completes the cross: the game is over, O wins
    b.play(cell)
    assert b.winner == O
    assert b.winning_cross.mask & (1 << cell)


def test_dense_endgame_loss_is_proven():
    b = dense_position(DENSE_LOSS_X, DENSE_LOSS_O)
    assert b.to_move == O
    anym = b.x | b.o
    free = FULL_MASK ^ anym
    x_threats = _threats(b.x, anym)
    # X has at least two distinct open threats (43 and 67 among them)
    assert (x_threats & (1 << 43)) and (x_threats & (1 << 67))
    assert _win_cells(b.o, free) == 0  # O cannot win now
    cell, val = ai_move(b.x, b.o, O)
    assert val == -1  # provably lost: O cannot stop both threats
    # no matter what O plays, X completes a cross on the next move
    o2 = b.o | (1 << cell)
    assert _win_cells(b.x, b.x | o2)


def test_lost_endgame_is_lost_after_every_move():
    b = dense_position(DENSE_LOSS_X, DENSE_LOSS_O)
    free = FULL_MASK ^ (b.x | b.o)
    t = free
    while t:
        lsb = t & -t
        t ^= lsb
        o2 = b.o | lsb
        v = _search(b.x, o2, X, -INF, INF, [1_000_000])
        assert v == 1  # X wins no matter what O plays


def test_search_values_are_win_or_loss():
    # Draws are impossible on this board (the cross hypergraph is not
    # 2-colorable), so every exact evaluation must be +1 or -1.
    for x_cells, o_cells in (
        (DENSE_WIN_X, DENSE_WIN_O),
        (DENSE_LOSS_X, DENSE_LOSS_O),
    ):
        b = dense_position(x_cells, o_cells)
        side = b.to_move
        _cell, val = ai_move(b.x, b.o, side)
        assert val in (1, -1)


def test_search_is_independent_of_transposition_table():
    b = dense_position(DENSE_WIN_X, DENSE_WIN_O)
    from game import ai as ai_mod

    v1 = _search(b.x, b.o, O, -INF, INF, [1_000_000])
    ai_mod._TT.clear()
    v2 = _search(b.x, b.o, O, -INF, INF, [1_000_000])
    assert v1 == v2 == 1


# ----------------------------------------------------------------- behavior

def test_ai_is_deterministic():
    b = replay([CROSS, ARM_X1, ARM_X2, ARM_Y1], AWAY_O[:3])
    m1, v1 = ai_move(b.x, b.o, O)
    m2, v2 = ai_move(b.x, b.o, O)
    assert (m1, v1) == (m2, v2)


def test_ai_opens_with_center_reply():
    # Second move on an otherwise empty board: the center sits on the most
    # live crosses (780) and must beat any corner or edge cell.
    b = replay([idx_of((0, 0, 0, 0))], [])
    assert b.to_move == O
    cell, _val = ai_move(b.x, b.o, O)
    assert cell == idx_of((1, 1, 1, 1))


def test_ai_takes_win_over_block():
    # X holds a double threat (43 via ARM_Y1, 18 via the mirror of its
    # fifth cell); O owns four cells of its own cross and can win now.
    # Taking the win dominates any block.
    # O's cross: X-axis {12, 13, 14} plus Y-axis {10, 13, 15} through 13.
    b = replay(
        [CROSS, ARM_X1, ARM_X2, ARM_Y1, idx_of((2, 2, 0, 2))],
        [idx_of((1, 1, 1, 0)), idx_of((0, 1, 1, 0)), idx_of((2, 1, 1, 0)),
         idx_of((1, 0, 1, 0))],
    )
    assert b.to_move == O
    x_threat = _threats(b.x, b.x | b.o)
    assert x_threat == (1 << ARM_Y2) | (1 << 18)  # X has two open threats
    wins = _win_cells(b.o, FULL_MASK ^ (b.x | b.o))
    assert wins == 1 << idx_of((1, 2, 1, 0))  # O can win now
    cell, val = ai_move(b.x, b.o, O)
    assert cell == idx_of((1, 2, 1, 0))
    assert val == 1


def test_ai_loses_when_double_threat_is_unstoppable():
    # X owns 4 cells of two different crosses with two different open ends:
    # whatever O plays, X completes one cross next.
    # cross A: X-axis + Y-axis through 40, missing ARM_Y2 (43)
    # cross B: X-axis + W-axis through 40, missing ARM_W2 (67)
    # X needs {39, 40, 41, 37} for A and {39, 40, 41, 13} for B ->
    b = replay(
        [ARM_X1, CROSS, ARM_X2, ARM_Y1, idx_of((1, 1, 1, 0))],
        [idx_of((0, 0, 0, 0)), idx_of((2, 0, 0, 0)), idx_of((0, 2, 0, 0)),
         idx_of((0, 0, 2, 0))],
    )
    assert b.to_move == O
    threats = _threats(b.x, b.x | b.o)
    assert threats == (1 << ARM_Y2) | (1 << 67)
    assert threats.bit_count() == 2
    cell, val = ai_move(b.x, b.o, O)
    assert val == -1
    # and X really does win on the next move
    o2 = b.o | (1 << cell)
    assert _win_cells(b.x, FULL_MASK ^ (b.x | o2))
