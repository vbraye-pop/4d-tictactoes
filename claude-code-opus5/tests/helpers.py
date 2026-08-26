"""Shared test helpers: an independent reference solver and position builders."""

from itertools import product

from fourd.board import O, X, other, winning_cross_through
from fourd.crosses import RULES_4D

# Threat-free positions found with a SAT solver: no cross is complete and
# neither player can complete one on their next move, so a solver has to look
# further than one ply.  Keyed by the number of empty cells.
QUIET_ENDGAMES = {
    9: {
        "x": [1, 5, 6, 7, 8, 13, 15, 17, 23, 24, 26, 28, 29, 33, 35, 36, 37, 39,
              42, 46, 48, 49, 50, 53, 56, 58, 59, 60, 61, 62, 64, 66, 68, 70, 71, 76],
        "o": [0, 3, 4, 9, 10, 12, 14, 16, 18, 19, 21, 22, 25, 30, 31, 32, 34, 38,
              41, 43, 44, 45, 47, 51, 52, 54, 55, 57, 63, 67, 69, 72, 73, 74, 75, 78],
    },
    13: {
        "x": [1, 4, 10, 11, 14, 15, 16, 17, 18, 20, 21, 22, 30, 31, 32, 34, 36,
              39, 45, 47, 51, 52, 53, 56, 65, 66, 67, 72, 73, 74, 75, 77, 79, 80],
        "o": [0, 3, 5, 6, 7, 8, 9, 12, 13, 24, 25, 28, 29, 33, 35, 37, 38, 40, 41,
              44, 46, 48, 49, 50, 54, 57, 58, 60, 61, 63, 64, 69, 70, 76],
    },
}


def masks(x_cells, o_cells):
    x = o = 0
    for cell in x_cells:
        x |= 1 << cell
    for cell in o_cells:
        o |= 1 << cell
    return x, o


def side_to_move(x_cells, o_cells):
    return X if len(x_cells) == len(o_cells) else O


def empty_cells(x_mask, o_mask):
    occupied = x_mask | o_mask
    return [cell for cell in range(RULES_4D.cell_count) if not occupied >> cell & 1]


def reference_value(x_mask: int, o_mask: int, player: str) -> int:
    """Plain minimax, no pruning and no shared code with the AI.

    Returns 1 if `player` (to move) wins with best play, 0 for a draw and -1
    for a loss.  Only used on positions with few empty cells.
    """
    empty = empty_cells(x_mask, o_mask)
    if not empty:
        return 0
    best = -1
    for cell in empty:
        if player == X:
            next_x, next_o = x_mask | 1 << cell, o_mask
            mine = next_x
        else:
            next_x, next_o = x_mask, o_mask | 1 << cell
            mine = next_o
        if winning_cross_through(RULES_4D, mine, cell) is not None:
            return 1
        best = max(best, -reference_value(next_x, next_o, other(player)))
    return best


def reference_move_values(x_mask: int, o_mask: int, player: str) -> dict[int, int]:
    values = {}
    for cell in empty_cells(x_mask, o_mask):
        if player == X:
            next_x, next_o = x_mask | 1 << cell, o_mask
            mine = next_x
        else:
            next_x, next_o = x_mask, o_mask | 1 << cell
            mine = next_o
        values[cell] = (1 if winning_cross_through(RULES_4D, mine, cell) is not None
                        else -reference_value(next_x, next_o, other(player)))
    return values


def crosses_from_definition(ndim: int = 4):
    """Re-derive the crosses straight from the task definition, independently."""
    cells = list(product(range(3), repeat=ndim))
    directions = [d for d in product((-1, 0, 1), repeat=ndim) if any(d)]
    found = set()
    for centre in cells:
        for d1 in directions:
            for d2 in directions:
                if d2 == d1 or d2 == tuple(-v for v in d1):
                    continue
                points = [centre]
                for step in (d1, d2):
                    for sign in (-1, 1):
                        points.append(tuple(centre[i] + sign * step[i] for i in range(ndim)))
                if all(all(0 <= v < 3 for v in point) for point in points):
                    found.add(frozenset(points))
    return found


def immediate_wins(mine: int, occupied: int) -> list[int]:
    """Empty cells that would complete a cross for the owner of `mine`."""
    wins = []
    for cell in range(RULES_4D.cell_count):
        if occupied >> cell & 1:
            continue
        if winning_cross_through(RULES_4D, mine | 1 << cell, cell) is not None:
            wins.append(cell)
    return wins


def quiet_filler(taken, count):
    """`count` cells outside `taken` that give their owner no immediate win."""
    chosen: list[int] = []
    mine = 0
    for cell in range(RULES_4D.cell_count):
        if len(chosen) == count:
            break
        if cell in taken:
            continue
        occupied = mine | 1 << cell
        for other_cell in taken:
            occupied |= 1 << other_cell
        if immediate_wins(mine | 1 << cell, occupied):
            continue
        chosen.append(cell)
        mine |= 1 << cell
    if len(chosen) != count:
        raise AssertionError("could not build a quiet filler set")
    return chosen
