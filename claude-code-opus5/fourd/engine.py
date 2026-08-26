"""Incremental search position for 4D tic-tac-toe.

Every cross keeps a running count of each player's marks.  From those counts we
maintain, in step with make/unmake, a static evaluation and a per-player map of
"cells that win immediately".  That map is what makes the search cheap: a side
with a completed-cross-in-one either wins on the spot or forces the opponent's
reply, so most nodes have a single legal candidate worth looking at.
"""

from __future__ import annotations

from .board import O, X
from .crosses import RULES_4D

# Value of owning n cells of an otherwise empty cross.
CROSS_VALUE = (0, 1, 7, 45, 400, 4000)
WIN_SCORE = 1_000_000


class Position:
    __slots__ = (
        "rules", "cross_masks", "cell_crosses", "boards", "occupied",
        "count_x", "count_o", "score", "threats", "n_cells",
    )

    def __init__(self, x_mask: int = 0, o_mask: int = 0, rules=RULES_4D):
        self.rules = rules
        self.cross_masks = rules.cross_masks
        self.cell_crosses = rules.cell_crosses
        self.n_cells = rules.cell_count
        self.boards = {X: 0, O: 0}
        self.occupied = 0
        n = len(rules.cross_masks)
        self.count_x = [0] * n
        self.count_o = [0] * n
        self.score = 0
        self.threats = {X: {}, O: {}}
        for cell in _bits(x_mask):
            self.make(cell, X)
        for cell in _bits(o_mask):
            self.make(cell, O)

    def empty_cells(self) -> list[int]:
        occupied = self.occupied
        return [c for c in range(self.n_cells) if not occupied >> c & 1]

    def winning_cells(self, player: str) -> list[int]:
        return list(self.threats[player])

    def make(self, cell: int, player: str) -> None:
        bit = 1 << cell
        self.boards[player] |= bit
        self.occupied |= bit
        occupied = self.occupied

        if player == X:
            mine, theirs, my_threats, their_threats, sign = (
                self.count_x, self.count_o, self.threats[X], self.threats[O], 1)
        else:
            mine, theirs, my_threats, their_threats, sign = (
                self.count_o, self.count_x, self.threats[O], self.threats[X], -1)

        masks = self.cross_masks
        delta = 0
        for k in self.cell_crosses[cell]:
            a = mine[k]
            b = theirs[k]
            mine[k] = a + 1
            if b:
                if a == 0:
                    delta += CROSS_VALUE[b]
                    if b == 4:
                        _drop(their_threats, cell)
            else:
                delta += CROSS_VALUE[a + 1] - CROSS_VALUE[a]
                if a == 3:
                    empty = masks[k] & ~occupied
                    if empty:
                        my_threats[empty.bit_length() - 1] = (
                            my_threats.get(empty.bit_length() - 1, 0) + 1)
                elif a == 4:
                    _drop(my_threats, cell)
        self.score += sign * delta

    def unmake(self, cell: int, player: str) -> None:
        occupied = self.occupied
        masks = self.cross_masks

        if player == X:
            mine, theirs, my_threats, their_threats, sign = (
                self.count_x, self.count_o, self.threats[X], self.threats[O], 1)
        else:
            mine, theirs, my_threats, their_threats, sign = (
                self.count_o, self.count_x, self.threats[O], self.threats[X], -1)

        delta = 0
        for k in self.cell_crosses[cell]:
            a = mine[k] - 1
            b = theirs[k]
            mine[k] = a
            if b:
                if a == 0:
                    delta += CROSS_VALUE[b]
                    if b == 4:
                        their_threats[cell] = their_threats.get(cell, 0) + 1
            else:
                delta += CROSS_VALUE[a + 1] - CROSS_VALUE[a]
                if a == 3:
                    empty = masks[k] & ~occupied
                    if empty:
                        _drop(my_threats, empty.bit_length() - 1)
                elif a == 4:
                    my_threats[cell] = my_threats.get(cell, 0) + 1
        self.score -= sign * delta

        bit = 1 << cell
        self.boards[player] &= ~bit
        self.occupied &= ~bit

    def move_values(self, player: str) -> dict[int, int]:
        """Static worth of each empty cell, used only for move ordering."""
        count_mine, count_theirs = (
            (self.count_x, self.count_o) if player == X else (self.count_o, self.count_x))
        values: dict[int, int] = {}
        occupied = self.occupied
        for cell in range(self.n_cells):
            if occupied >> cell & 1:
                continue
            total = 0
            for k in self.cell_crosses[cell]:
                a = count_mine[k]
                b = count_theirs[k]
                if b == 0:
                    total += CROSS_VALUE[a + 1] - CROSS_VALUE[a]
                elif a == 0:
                    total += CROSS_VALUE[b + 1] - CROSS_VALUE[b]
            values[cell] = total
        return values


def _drop(threats: dict[int, int], cell: int) -> None:
    left = threats.get(cell, 0) - 1
    if left > 0:
        threats[cell] = left
    else:
        threats.pop(cell, None)


def _bits(mask: int):
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low
