"""AI opponent: forced-line logic plus exact endgame search.

Move selection, in priority order:

1. Take an immediate win if one exists.
2. If the opponent has two or more distinct winning cells, the position is
   provably lost; play the best principled move anyway.
3. If the opponent has exactly one winning cell, blocking it is the only
   move that does not lose at once. In endgame positions the blocked line is
   evaluated exactly; otherwise the block is played.
4. In endgame positions (at most EXACT_EMPTY_MAX empty cells), search exactly
   with alpha-beta and forced-line pruning; the returned value is provable.
5. Everywhere else, play the highest-scoring principled move: complete a
   cross, build a double threat (fork), build a threat, block a threat, then
   maximize live-cross potential with a small center bias. Never random.

Values are from the AI's perspective: +1 win, 0 draw, -1 loss, None when the
position was not searched to a proof.
"""

from __future__ import annotations

from .board import CROSS_MASKS, CELL_CROSS_NEEDS, FULL_MASK, O, X, coord_of

EXACT_EMPTY_MAX = 12
NODE_BUDGET = 300_000

INF = 10**12
FORK_BONUS = 10**9
BLOCK_BONUS = 10**6
THREAT_BONUS = 10**3

_EXACT = 0
_LOWER = 1
_UPPER = 2

_TT: dict[tuple[int, int, int], tuple[int, int]] = {}


class _Abort(Exception):
    """Node budget exhausted; the running search is not provably complete."""


def _centrality(cell: int) -> int:
    return sum(1 for c in coord_of(cell) if c == 1)


_CENTRALITY = tuple(_centrality(cell) for cell in range(FULL_MASK.bit_length()))


def _win_cells(side_mask: int, free: int) -> int:
    """Bitmask of empty cells where `side_mask` completes a cross now."""
    out = 0
    t = free
    while t:
        lsb = t & -t
        cell = lsb.bit_length() - 1
        for need in CELL_CROSS_NEEDS[cell]:
            if (side_mask & need) == need:
                out |= lsb
                break
        t ^= lsb
    return out


def _threats(mask: int, any_mask: int) -> int:
    """Bitmask of empty cells where the holder of `mask` completes a cross.

    A threat is a cross holding four of the side's cells plus one empty
    cell; the empty cell is where the side would complete it.
    """
    out = 0
    free = FULL_MASK ^ any_mask
    other = any_mask ^ mask
    for cm in CROSS_MASKS:
        if cm & other:
            continue
        e = cm & free
        if e and not (e & (e - 1)):
            out |= e
    return out


def _move_score(
    side_mask: int,
    opp_mask: int,
    cell: int,
    lsb: int,
    new_any: int,
) -> int:
    """Heuristic score of placing side's mark on `cell`."""
    created = 0
    potential = 0
    threat_cells = set()
    for need in CELL_CROSS_NEEDS[cell]:
        cm = need | lsb
        if cm & opp_mask:
            continue
        if (side_mask & need) == need:
            return INF
        e = cm & ~new_any
        bc = e.bit_count()
        if bc == 1:
            threat_cells.add(e)
        elif bc == 2:
            potential += 3
        elif bc >= 3:
            potential += 1
    created = len(threat_cells)
    score = created * THREAT_BONUS + potential
    if created >= 2:
        score += FORK_BONUS
    return score + _CENTRALITY[cell]


def _ordered_moves(
    x: int,
    o: int,
    side: int,
    free: int,
) -> list[tuple[int, int, int]]:
    """Moves as (score, cell, bit) sorted best first, ties by cell index."""
    side_mask = x if side == X else o
    opp_mask = o if side == X else x
    any_mask = x | o
    moves = []
    t = free
    while t:
        lsb = t & -t
        cell = lsb.bit_length() - 1
        moves.append((_move_score(side_mask, opp_mask, cell, lsb, any_mask | lsb), cell, lsb))
        t ^= lsb
    moves.sort(key=lambda item: (-item[0], item[1]))
    return moves


def _search(x: int, o: int, side: int, alpha: int, beta: int, budget: list[int]) -> int:
    """Exact negamax with alpha-beta, transposition table, forced-line pruning."""
    budget[0] -= 1
    if budget[0] < 0:
        raise _Abort
    key = (x, o, side)
    hit = _TT.get(key)
    orig_alpha = alpha
    if hit is not None:
        flag, val = hit
        if flag == _EXACT:
            return val
        if flag == _LOWER:
            alpha = max(alpha, val)
        else:
            beta = min(beta, val)
        if alpha >= beta:
            return val

    any_mask = x | o
    free = FULL_MASK ^ any_mask
    if free == 0:
        val = 0
    else:
        side_mask = x if side == X else o
        opp_mask = o if side == X else x
        win = _win_cells(side_mask, free)
        if win:
            val = 1
        else:
            opp_threats = _threats(opp_mask, any_mask)
            tc = opp_threats.bit_count()
            if tc >= 2:
                # The opponent completes a cross whatever we play.
                val = -1
            elif tc == 1:
                # Only the block survives; everything else loses at once.
                block = opp_threats
                if side == X:
                    val = -_search(x | block, o, O, -beta, -alpha, budget)
                else:
                    val = -_search(x, o | block, X, -beta, -alpha, budget)
            else:
                val = _branch(x, o, side, any_mask, free, alpha, beta, budget)

    if val <= orig_alpha:
        flag = _UPPER
    elif val >= beta:
        flag = _LOWER
    else:
        flag = _EXACT
    _TT[key] = (flag, val)
    return val


def _branch(
    x: int,
    o: int,
    side: int,
    any_mask: int,
    free: int,
    alpha: int,
    beta: int,
    budget: list[int],
) -> int:
    side_mask = x if side == X else o
    opp_mask = o if side == X else x
    best = -1
    for score, cell, lsb in _ordered_moves(x, o, side, free):
        if score >= INF:
            best = 1
            break
        if side == X:
            v = -_search(x | lsb, o, O, -beta, -alpha, budget)
        else:
            v = -_search(x, o | lsb, X, -beta, -alpha, budget)
        if v > best:
            best = v
        if v > alpha:
            alpha = v
        if alpha >= beta:
            break
    return best


def _best_heuristic(
    x: int,
    o: int,
    side: int,
    free: int,
    opp_threat_mask: int,
) -> int:
    """Best move by score alone; deterministic ties by cell index."""
    side_mask = x if side == X else o
    opp_mask = o if side == X else x
    any_mask = x | o
    best_cell = -1
    best_score = None
    t = free
    while t:
        lsb = t & -t
        cell = lsb.bit_length() - 1
        score = _move_score(side_mask, opp_mask, cell, lsb, any_mask | lsb)
        if lsb & opp_threat_mask:
            score += BLOCK_BONUS
        if best_score is None or score > best_score:
            best_score = score
            best_cell = cell
        t ^= lsb
    return best_cell


def ai_move(x: int, o: int, side: int) -> tuple[int | None, int | None]:
    """Choose a move for `side`. Returns (cell, proven value or None)."""
    _TT.clear()
    budget = [NODE_BUDGET]
    any_mask = x | o
    free = FULL_MASK ^ any_mask
    if free == 0:
        return None, 0
    side_mask = x if side == X else o
    opp_mask = o if side == X else x

    win = _win_cells(side_mask, free)
    if win:
        return (win & -win).bit_length() - 1, 1

    opp_threats = _threats(opp_mask, any_mask)
    tc = opp_threats.bit_count()
    if tc >= 2:
        return _best_heuristic(x, o, side, free, opp_threats), -1

    empties = free.bit_count()
    if tc == 1:
        block = opp_threats
        cell = block.bit_length() - 1
        if empties <= EXACT_EMPTY_MAX:
            try:
                if side == X:
                    val = -_search(x | block, o, O, -INF, INF, budget)
                else:
                    val = -_search(x, o | block, X, -INF, INF, budget)
            except _Abort:
                val = None
            return cell, val
        return cell, None

    if empties <= EXACT_EMPTY_MAX:
        best_cell = -1
        best_val = -1
        alpha = -1
        try:
            for score, cell, lsb in _ordered_moves(x, o, side, free):
                if score >= INF:
                    return cell, 1
                if side == X:
                    v = -_search(x | lsb, o, O, -1, -alpha, budget)
                else:
                    v = -_search(x, o | lsb, X, -1, -alpha, budget)
                if v > best_val:
                    best_val = v
                    best_cell = cell
                if v > alpha:
                    alpha = v
                    if alpha >= 1:
                        break
        except _Abort:
            if best_cell < 0:
                return _best_heuristic(x, o, side, free, opp_threats), None
            return best_cell, None
        return best_cell, best_val

    return _best_heuristic(x, o, side, free, opp_threats), None
