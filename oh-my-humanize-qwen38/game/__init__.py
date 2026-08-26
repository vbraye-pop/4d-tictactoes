"""4D tic-tac-toe: rules engine and AI."""

from .board import (
    CROSSES,
    CROSS_MASKS,
    CROSS_MASK_SET,
    CELL_CROSSES,
    FULL_MASK,
    N_CELLS,
    O,
    X,
    Board,
    Cross,
    IllegalMove,
    coord_of,
    idx_of,
)
from .ai import EXACT_EMPTY_MAX, ai_move

__all__ = [
    "CROSSES",
    "CROSS_MASKS",
    "CROSS_MASK_SET",
    "CELL_CROSSES",
    "FULL_MASK",
    "N_CELLS",
    "O",
    "X",
    "Board",
    "Cross",
    "IllegalMove",
    "coord_of",
    "idx_of",
    "EXACT_EMPTY_MAX",
    "ai_move",
]
