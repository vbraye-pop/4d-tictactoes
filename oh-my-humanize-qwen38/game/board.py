"""Board, rules, and winning-cross geometry for 4D tic-tac-toe.

The board is 3x3x3x3, 81 cells. A cell index is x + 3*y + 9*z + 27*w with
every coordinate in {0, 1, 2}. A winning cross is the five cells
{c, c-d1, c+d1, c-d2, c+d2}: two straight 3-cell lines crossing at their
common middle cell. The board contains exactly 1548 distinct crosses.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

SIZE = 3
DIMS = 4
N_CELLS = SIZE ** DIMS
FULL_MASK = (1 << N_CELLS) - 1

X = 0
O = 1
PLAYER_NAMES = ("X", "O")

_BASES = tuple(SIZE**i for i in range(DIMS))  # (1, 3, 9, 27)


def coord_of(cell: int) -> tuple[int, int, int, int]:
    """Coordinates (x, y, z, w) of a cell index."""
    return tuple((cell // base) % SIZE for base in _BASES)


def idx_of(coords: tuple[int, int, int, int]) -> int:
    return sum(c * b for c, b in zip(coords, _BASES))


def _all_directions() -> tuple[tuple[int, int, int, int], ...]:
    """The 40 undirected grid directions, in canonical form."""
    dirs = []
    for v in product((-1, 0, 1), repeat=DIMS):
        if all(e == 0 for e in v):
            continue
        first = next(e for e in v if e != 0)
        if first == 1:
            dirs.append(v)
    return tuple(dirs)


DIRECTIONS = _all_directions()


@dataclass(frozen=True)
class Cross:
    mask: int
    center: int
    line1: tuple[int, int, int]
    line2: tuple[int, int, int]
    cells: tuple[int, int, int, int, int]


def _generate_crosses() -> list[Cross]:
    crosses = []
    seen = set()
    for center in range(N_CELLS):
        cc = coord_of(center)
        # A 3-cell line through the center fits the board exactly when every
        # axis the direction uses points at a center coordinate of 1.
        lines = []
        for d in DIRECTIONS:
            if any(d[i] != 0 and cc[i] != 1 for i in range(DIMS)):
                continue
            a = idx_of(tuple(cc[i] - d[i] for i in range(DIMS)))
            b = idx_of(tuple(cc[i] + d[i] for i in range(DIMS)))
            lines.append((1 << a | 1 << center | 1 << b, a, b))
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                mask = lines[i][0] | lines[j][0]
                if mask in seen:
                    continue
                seen.add(mask)
                crosses.append(
                    Cross(
                        mask=mask,
                        center=center,
                        line1=(lines[i][1], center, lines[i][2]),
                        line2=(lines[j][1], center, lines[j][2]),
                        cells=(
                            lines[i][1],
                            center,
                            lines[i][2],
                            lines[j][1],
                            lines[j][2],
                        ),
                    )
                )
    return crosses


CROSSES = tuple(_generate_crosses())
assert len(CROSSES) == 1548, f"expected 1548 crosses, got {len(CROSSES)}"
assert len({c.mask for c in CROSSES}) == 1548

CROSS_MASKS = tuple(c.mask for c in CROSSES)
CROSS_MASK_SET = frozenset(CROSS_MASKS)

CELL_CROSSES: tuple[tuple[Cross, ...], ...] = tuple(
    tuple(c for c in CROSSES if cell in c.cells) for cell in range(N_CELLS)
)
# For fast win checks: the four cells of a cross other than `cell`, one entry
# per cross containing the cell. Playing `cell` wins iff side_mask covers need.
CELL_CROSS_NEEDS: tuple[tuple[int, ...], ...] = tuple(
    tuple(c.mask ^ (1 << cell) for c in CELL_CROSSES[cell])
    for cell in range(N_CELLS)
)


class IllegalMove(Exception):
    pass


class Board:
    __slots__ = (
        "x",
        "o",
        "to_move",
        "last_move",
        "winner",
        "winning_cross",
        "moves",
    )

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.x = 0
        self.o = 0
        self.to_move = X
        self.last_move = None
        self.winner = None
        self.winning_cross = None
        self.moves: list[int] = []

    def mask_of(self, player: int) -> int:
        return self.x if player == X else self.o

    def occupant(self, cell: int) -> int | None:
        bit = 1 << cell
        if self.x & bit:
            return X
        if self.o & bit:
            return O
        return None

    @property
    def is_over(self) -> bool:
        return self.winner is not None or self.full

    @property
    def draw(self) -> bool:
        """True when the board is full and no cross has been formed.

        By the non-2-colorability of the 1548-cross hypergraph, every
        filled board contains a monochromatic cross, so a real game always
        ends in a win; this rule is implemented per spec and is reachable
        in the state machine directly.
        """
        return self.winner is None and self.full

    @property
    def full(self) -> bool:
        return (self.x | self.o) == FULL_MASK

    def move_count(self) -> int:
        return (self.x | self.o).bit_count()

    def is_legal(self, cell: int) -> bool:
        if not isinstance(cell, int) or isinstance(cell, bool):
            return False
        return 0 <= cell < N_CELLS and not self.is_over and self.occupant(cell) is None

    def play(self, cell: int) -> None:
        """Place the current player's mark on an empty cell.

        Raises IllegalMove when the cell is out of range, occupied, or the
        game already ended. Updates the winner, draw, and turn state.
        """
        if not self.is_legal(cell):
            raise IllegalMove(f"cell {cell} is not a legal move")
        bit = 1 << cell
        mask = self.mask_of(self.to_move) | bit
        if self.to_move == X:
            self.x = mask
        else:
            self.o = mask
        self.last_move = cell
        self.moves.append(cell)
        for cross in CELL_CROSSES[cell]:
            if (mask & cross.mask) == cross.mask:
                self.winner = self.to_move
                self.winning_cross = cross
                break
        if not self.is_over:
            self.to_move = O if self.to_move == X else X

    def empty_cells(self) -> list[int]:
        free = FULL_MASK ^ (self.x | self.o)
        out = []
        while free:
            lsb = free & -free
            out.append(lsb.bit_length() - 1)
            free ^= lsb
        return out
