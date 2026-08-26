"""Move selection for 4D tic-tac-toe.

Three layers, in order of authority:

1.  Tactics.  Complete a cross if one is available; otherwise block the
    opponent's.  Both are forced in the game-theoretic sense.
2.  Exact solution.  A full alpha-beta search with a transposition table, given
    a time budget.  The board is dense enough in threats that this usually
    finishes well before the endgame; near the end it always does.
3.  Threat search.  When the exact search runs out of time, an
    iterative-deepening alpha-beta over the most promising cells, guided by how
    close each cross is to completion.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .board import O, X, other
from .engine import WIN_SCORE, Position

ENDGAME_EMPTY_CELLS = 16
ENDGAME_BUDGET = 1.5
SOLVE_ATTEMPT = 0.5
ROOT_WIDTH = 16
INNER_WIDTH = 8
MAX_DEPTH = 8
DEFAULT_BUDGET = 1.0

EXACT, LOWER, UPPER = 0, 1, 2


@dataclass
class Decision:
    cell: int
    reason: str
    detail: str
    exact: bool = False
    value: int | None = None
    depth: int = 0
    nodes: int = 0
    elapsed: float = 0.0


class _Timeout(Exception):
    pass


def choose_move(x_mask: int, o_mask: int, player: str,
                budget: float = DEFAULT_BUDGET) -> Decision:
    started = time.perf_counter()
    position = Position(x_mask, o_mask)
    empty = position.empty_cells()
    if not empty:
        raise ValueError("no legal moves")

    opponent = other(player)
    values = position.move_values(player)

    wins = position.winning_cells(player)
    if wins:
        cell = max(wins, key=lambda c: (values[c], -c))
        return Decision(cell, "win", "completes a cross", exact=True, value=1,
                        elapsed=time.perf_counter() - started)

    blocks = position.winning_cells(opponent)
    if blocks:
        cell = max(blocks, key=lambda c: (values[c], -c))
        detail = ("blocks the opponent's cross" if len(blocks) == 1
                  else f"blocks one of {len(blocks)} opponent threats")
        return Decision(cell, "block", detail, exact=len(blocks) == 1,
                        value=None, elapsed=time.perf_counter() - started)

    endgame = len(empty) <= ENDGAME_EMPTY_CELLS
    solved = _solve_exactly(position, player, empty, values,
                            ENDGAME_BUDGET if endgame else SOLVE_ATTEMPT)
    if solved is not None:
        solved.elapsed = time.perf_counter() - started
        return solved

    decision = _threat_search(position, player, empty, values, budget)
    decision.elapsed = time.perf_counter() - started
    return decision


def _ordered(cells, values, width=None):
    ordered = sorted(cells, key=lambda c: (-values[c], c))
    return ordered if width is None else ordered[:width]


def _solve_exactly(position: Position, player: str, empty, values,
                   budget: float) -> Decision | None:
    table: dict[tuple[int, int], tuple[int, int]] = {}
    deadline = time.perf_counter() + budget
    counter = [0]
    best_cell, best_value = None, -2
    alpha = -1
    try:
        for cell in _ordered(empty, values):
            position.make(cell, player)
            try:
                value = -_solve(position, other(player), -1, -alpha, table, counter, deadline)
            finally:
                position.unmake(cell, player)
            if value > best_value:
                best_cell, best_value = cell, value
                alpha = max(alpha, value)
            if best_value == 1:
                break
    except _Timeout:
        return None

    label = {1: "wins by force", 0: "holds the draw", -1: "position is lost"}[best_value]
    return Decision(best_cell, "solved", f"solved to the end: {label}", exact=True,
                    value=best_value, depth=len(empty), nodes=counter[0])


def _solve(position: Position, player: str, alpha: int, beta: int, table, counter,
           deadline: float) -> int:
    """Exact value for `player` to move: 1 win, 0 draw, -1 loss."""
    counter[0] += 1
    if not counter[0] % 1024 and time.perf_counter() > deadline:
        raise _Timeout

    if position.winning_cells(player):
        return 1
    opponent = other(player)
    threats = position.winning_cells(opponent)
    if len(threats) > 1:
        return -1

    key = (position.boards[X], position.boards[O])
    entry = table.get(key)
    if entry is not None:
        value, flag = entry
        if flag == EXACT:
            return value
        if flag == LOWER and value >= beta:
            return value
        if flag == UPPER and value <= alpha:
            return value

    if threats:
        moves = threats
    else:
        moves = position.empty_cells()
        if not moves:
            return 0
        if len(moves) > 3:
            moves = _ordered(moves, position.move_values(player))

    original_alpha = alpha
    best = -2
    for cell in moves:
        position.make(cell, player)
        try:
            value = -_solve(position, opponent, -beta, -alpha, table, counter, deadline)
        finally:
            position.unmake(cell, player)
        if value > best:
            best = value
            if value > alpha:
                alpha = value
                if alpha >= beta:
                    break

    flag = EXACT
    if best <= original_alpha:
        flag = UPPER
    elif best >= beta:
        flag = LOWER
    table[key] = (best, flag)
    return best


def _threat_search(position: Position, player: str, empty, values,
                   budget: float) -> Decision:
    deadline = time.perf_counter() + budget
    counter = [0]
    candidates = _ordered(empty, values, ROOT_WIDTH)
    best_cell = candidates[0]
    best_value = 0
    reached = 0

    for depth in range(2, MAX_DEPTH + 1):
        if depth > 2 and time.perf_counter() > deadline - budget / 2:
            break
        alpha, local_best, local_cell = -WIN_SCORE * 2, -WIN_SCORE * 2, None
        try:
            for cell in candidates:
                position.make(cell, player)
                try:
                    value = -_search(position, other(player), depth - 1, -WIN_SCORE * 2,
                                     -alpha, 1, counter, deadline)
                finally:
                    position.unmake(cell, player)
                if value > local_best:
                    local_best, local_cell = value, cell
                    alpha = max(alpha, value)
        except _Timeout:
            break
        best_cell, best_value, reached = local_cell, local_best, depth
        candidates = sorted(candidates, key=lambda c: (c != local_cell, -values[c], c))
        if abs(best_value) >= WIN_SCORE - 100:
            break
        if time.perf_counter() > deadline:
            break

    if best_value >= WIN_SCORE - 100:
        detail = "forced win found"
    elif best_value <= -WIN_SCORE + 100:
        detail = "defending a lost position"
    else:
        detail = "builds toward a cross"
    return Decision(best_cell, "search", detail, exact=False, value=None,
                    depth=reached, nodes=counter[0])


def _search(position: Position, player: str, depth: int, alpha: int, beta: int,
            ply: int, counter, deadline: float) -> int:
    counter[0] += 1
    if not counter[0] % 512 and time.perf_counter() > deadline:
        raise _Timeout

    if position.winning_cells(player):
        return WIN_SCORE - ply
    opponent = other(player)
    threats = position.winning_cells(opponent)
    if len(threats) > 1:
        return -(WIN_SCORE - ply - 1)

    if threats:
        moves = threats
        depth += 1  # a forced block costs nothing to look past
    else:
        if depth <= 0:
            return position.score if player == X else -position.score
        moves = _ordered(position.empty_cells(), position.move_values(player), INNER_WIDTH)
        if not moves:
            return 0

    best = -WIN_SCORE * 2
    for cell in moves:
        position.make(cell, player)
        try:
            value = -_search(position, opponent, depth - 1, -beta, -alpha, ply + 1,
                             counter, deadline)
        finally:
            position.unmake(cell, player)
        if value > best:
            best = value
            if value > alpha:
                alpha = value
                if alpha >= beta:
                    break
    return best
