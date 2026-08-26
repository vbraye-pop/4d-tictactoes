"""Game state for n-dimensional 3^n tic-tac-toe, stored as two bitboards."""

from __future__ import annotations

from dataclasses import dataclass, field

from .crosses import RULES_4D, Rules

X = "X"
O = "O"
PLAYERS = (X, O)

ONGOING = "ongoing"
WIN = "win"
DRAW = "draw"


def other(player: str) -> str:
    return O if player == X else X


def find_winning_cross(rules: Rules, mask: int) -> tuple[int, ...] | None:
    """Authoritative scan: any cross fully owned by the given bitboard."""
    for index, cross_mask in enumerate(rules.cross_masks):
        if mask & cross_mask == cross_mask:
            return rules.cross_cells[index]
    return None


def winning_cross_through(rules: Rules, mask: int, cell: int) -> tuple[int, ...] | None:
    """Same answer as find_winning_cross when `cell` was the last cell played."""
    for index in rules.cell_crosses[cell]:
        cross_mask = rules.cross_masks[index]
        if mask & cross_mask == cross_mask:
            return rules.cross_cells[index]
    return None


class IllegalMove(Exception):
    pass


@dataclass
class Game:
    rules: Rules = RULES_4D
    boards: dict[str, int] = field(default_factory=lambda: {X: 0, O: 0})
    to_move: str = X
    status: str = ONGOING
    winner: str | None = None
    winning_cross: tuple[int, ...] | None = None
    history: list[tuple[str, int]] = field(default_factory=list)

    @classmethod
    def from_cells(cls, x_cells, o_cells, to_move=None, rules: Rules = RULES_4D) -> "Game":
        """Build a position directly, for tests and for exploring endgames."""
        game = cls(rules=rules)
        for player, cells in ((X, x_cells), (O, o_cells)):
            for cell in cells:
                game.boards[player] |= 1 << cell
        if game.boards[X] & game.boards[O]:
            raise IllegalMove("a cell cannot hold both marks")
        counts = {p: bin(game.boards[p]).count("1") for p in PLAYERS}
        game.to_move = to_move or (X if counts[X] == counts[O] else O)
        game.history = [(X, cell) for cell in x_cells] + [(O, cell) for cell in o_cells]
        game._refresh_status()
        return game

    @property
    def occupied(self) -> int:
        return self.boards[X] | self.boards[O]

    @property
    def empty_cells(self) -> list[int]:
        occupied = self.occupied
        return [cell for cell in range(self.rules.cell_count) if not occupied >> cell & 1]

    @property
    def move_count(self) -> int:
        return bin(self.occupied).count("1")

    def owner(self, cell: int) -> str | None:
        for player in PLAYERS:
            if self.boards[player] >> cell & 1:
                return player
        return None

    def is_legal(self, cell: int) -> bool:
        if self.status != ONGOING:
            return False
        if not 0 <= cell < self.rules.cell_count:
            return False
        return not self.occupied >> cell & 1

    def play(self, cell: int) -> "Game":
        if self.status != ONGOING:
            raise IllegalMove("the game is over")
        if not 0 <= cell < self.rules.cell_count:
            raise IllegalMove(f"cell {cell} is off the board")
        if self.occupied >> cell & 1:
            raise IllegalMove(f"cell {cell} is already taken")

        player = self.to_move
        self.boards[player] |= 1 << cell
        self.history.append((player, cell))

        cross = winning_cross_through(self.rules, self.boards[player], cell)
        if cross is not None:
            self.status = WIN
            self.winner = player
            self.winning_cross = cross
        elif self.occupied == self.rules.full_mask:
            self.status = DRAW
        else:
            self.to_move = other(player)
        return self

    def _refresh_status(self) -> None:
        for player in PLAYERS:
            cross = find_winning_cross(self.rules, self.boards[player])
            if cross is not None:
                self.status, self.winner, self.winning_cross = WIN, player, cross
                return
        self.status = DRAW if self.occupied == self.rules.full_mask else ONGOING
        self.winner = None
        self.winning_cross = None
