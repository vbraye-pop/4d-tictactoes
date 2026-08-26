"""Winning crosses of n-dimensional 3x3x...x3 tic-tac-toe.

A cross is {c, c-d1, c+d1, c-d2, c+d2} for a centre cell c and two nonzero
direction vectors d1, d2 in {-1,0,1}^n with d2 not parallel to d1, all five
cells inside the board.  In four dimensions there are exactly 1548 of them.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

SIZE = 3


@dataclass(frozen=True)
class Rules:
    """Board geometry plus the derived cross tables used by everything else."""

    ndim: int
    cells: tuple[tuple[int, ...], ...]
    cross_cells: tuple[tuple[int, ...], ...]
    cross_masks: tuple[int, ...]
    cell_crosses: tuple[tuple[int, ...], ...]

    @property
    def cell_count(self) -> int:
        return len(self.cells)

    @property
    def full_mask(self) -> int:
        return (1 << len(self.cells)) - 1

    def index(self, coords) -> int:
        i = 0
        for value in coords:
            if not 0 <= value < SIZE:
                raise ValueError(f"coordinate out of range: {coords}")
            i = i * SIZE + value
        return i

    def coords(self, index: int) -> tuple[int, ...]:
        return self.cells[index]


def _directions(ndim: int) -> list[tuple[int, ...]]:
    return [d for d in product((-1, 0, 1), repeat=ndim) if any(d)]


def build_rules(ndim: int = 4) -> Rules:
    cells = tuple(product(range(SIZE), repeat=ndim))
    index_of = {cell: i for i, cell in enumerate(cells)}
    directions = _directions(ndim)

    found: set[frozenset[int]] = set()
    for centre in cells:
        arms: list[tuple[tuple[int, ...], list[int]]] = []
        for step in directions:
            ends = []
            for sign in (-1, 1):
                point = tuple(centre[i] + sign * step[i] for i in range(ndim))
                if not all(0 <= v < SIZE for v in point):
                    break
                ends.append(index_of[point])
            if len(ends) == 2:
                arms.append((step, ends))
        for i, (d1, ends1) in enumerate(arms):
            for d2, ends2 in arms[i + 1:]:
                if d2 == tuple(-v for v in d1):
                    continue
                found.add(frozenset([index_of[centre], *ends1, *ends2]))

    cross_cells = tuple(sorted(tuple(sorted(cross)) for cross in found))
    cross_masks = tuple(_mask(cross) for cross in cross_cells)

    per_cell: list[list[int]] = [[] for _ in cells]
    for cross_index, cross in enumerate(cross_cells):
        for cell in cross:
            per_cell[cell].append(cross_index)

    return Rules(
        ndim=ndim,
        cells=cells,
        cross_cells=cross_cells,
        cross_masks=cross_masks,
        cell_crosses=tuple(tuple(entry) for entry in per_cell),
    )


def _mask(cells) -> int:
    mask = 0
    for cell in cells:
        mask |= 1 << cell
    return mask


RULES_4D = build_rules(4)
