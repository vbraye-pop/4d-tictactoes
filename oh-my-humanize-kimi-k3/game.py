"""Core logic for 4D tic-tac-toe on a 3x3x3x3 board.

Board representation: flat list of 81 cells; index encodes (x, y, z, w)
with x the fastest-varying coordinate. Values are None, "X", or "O".
"""

from itertools import product, combinations

SIZE = 3
DIMS = 4
N_CELLS = SIZE ** DIMS
PLAYERS = ("X", "O")

DIRECTIONS = []  # canonical (first-nonzero-positive) sign vectors
for v in product((-1, 0, 1), repeat=DIMS):
    if all(c == 0 for c in v):
        continue
    for c in v:
        if c != 0:
            if c > 0:
                DIRECTIONS.append(v)
            break


def to_index(coords):
    idx = 0
    for c in coords:
        idx = idx * SIZE + c
    return idx


def to_coords(idx):
    coords = []
    for _ in range(DIMS):
        coords.append(idx % SIZE)
        idx //= SIZE
    return tuple(reversed(coords))


def _build_crosses():
    crosses = set()
    for center in product(range(SIZE), repeat=DIMS):
        for d1, d2 in combinations(DIRECTIONS, 2):
            cells = [center]
            for d in (d1, d2):
                for sign in (1, -1):
                    p = tuple(center[k] + sign * d[k] for k in range(DIMS))
                    if not all(0 <= p[k] < SIZE for k in range(DIMS)):
                        break
                    cells.append(p)
                else:
                    continue
                break
            else:
                crosses.add(tuple(sorted(to_index(c) for c in cells)))
    return sorted(crosses)


CROSSES = _build_crosses()

CROSSES_BY_CELL = [[] for _ in range(N_CELLS)]
for cross_idx, cross in enumerate(CROSSES):
    for cell in cross:
        CROSSES_BY_CELL[cell].append(cross_idx)


class Game:
    """Mutable game state. board: list of None/'X'/'O'; turn: current player."""

    def __init__(self, board=None, turn="X"):
        self.board = list(board) if board else [None] * N_CELLS
        self.turn = turn
        self.winner = None
        self.win_cross = None

    def legal_moves(self):
        return [i for i, v in enumerate(self.board) if v is None]

    def is_legal(self, cell):
        return 0 <= cell < N_CELLS and self.board[cell] is None and self.winner is None

    def move(self, cell):
        """Apply a move. Returns True if legal. Sets winner/draw on completion."""
        if not self.is_legal(cell):
            return False
        self.board[cell] = self.turn
        finished = self._check_finished(cell)
        if not finished:
            self.turn = other(self.turn)
        return True

    def _check_finished(self, cell):
        board = self.board
        player = self.turn
        for cross_idx in CROSSES_BY_CELL[cell]:
            cross = CROSSES[cross_idx]
            if all(board[c] == player for c in cross):
                self.winner = player
                self.win_cross = cross
                return True
        if all(v is not None for v in board):
            self.winner = "draw"
            return True
        return False

    def crosses_payload(self):
        return CROSSES


def other(player):
    return "O" if player == "X" else "X"


# ---------------- AI ----------------

ENDGAME_THRESHOLD = 9  # empties at/below which we solve exactly


def find_winning_move(board, player):
    """Index where `player` completes a cross, or None."""
    for cell, v in enumerate(board):
        if v is not None:
            continue
        for cross_idx in CROSSES_BY_CELL[cell]:
            cross = CROSSES[cross_idx]
            if sum(board[c] == player for c in cross) == 4:
                return cell
    return None


class AI:
    """Strong deterministic opponent.

    Priority: immediate win, block opponent win, exact endgame solve,
    heuristic maximise own potential crosses minus opponent's.
    """

    def __init__(self, endgame_threshold=ENDGAME_THRESHOLD):
        self.endgame_threshold = endgame_threshold

    def choose(self, game):
        board = game.board
        me = game.turn
        opp = other(me)

        move = find_winning_move(board, me)
        if move is not None:
            return move

        move = find_winning_move(board, opp)
        if move is not None:
            return move

        empties = [i for i, v in enumerate(board) if v is None]
        if len(empties) <= self.endgame_threshold:
            return self._solve(board, me, empties)

        return self._heuristic(board, me, opp, empties)

    # exact minimax; values are from `me`'s perspective (+1 win, -1 loss, 0 draw)
    def _solve(self, board, me, empties):
        memo = {}

        def score(board_tuple, player):
            if board_tuple in memo:
                return memo[board_tuple]
            empt = [i for i, v in enumerate(board_tuple) if v is None]
            if not empt:
                memo[board_tuple] = 0
                return 0
            best = -2 if player == me else 2
            for cell in empt:
                newb = list(board_tuple)
                newb[cell] = player
                won = any(
                    all(newb[c] == player for c in CROSSES[ci])
                    for ci in CROSSES_BY_CELL[cell]
                )
                if won:
                    val = 1 if player == me else -1
                else:
                    val = score(tuple(newb), other(player))
                if player == me:
                    best = max(best, val)
                else:
                    best = min(best, val)
            memo[board_tuple] = best
            return best

        board_tuple = tuple(board)
        best_move = None
        best_val = -2
        for cell in empties:
            newb = list(board_tuple)
            newb[cell] = me
            won = any(all(newb[c] == me for c in CROSSES[ci]) for ci in CROSSES_BY_CELL[cell])
            val = 1 if won else score(tuple(newb), other(me))
            if val > best_val:
                best_val = val
                best_move = cell
        return best_move

    def _heuristic(self, board, me, opp, empties):
        """Score cells: own live crosses weighted, minus opponent potential."""
        best_move = None
        best_score = None
        for cell in empties:
            score = 0.0
            for cross_idx in CROSSES_BY_CELL[cell]:
                cross = CROSSES[cross_idx]
                mine = sum(board[c] == me for c in cross)
                theirs = sum(board[c] == opp for c in cross)
                if mine and theirs:
                    continue
                if mine:
                    score += 4 ** (mine)  # extend partial crosses superlinearly
                elif theirs:
                    score -= 3 ** theirs
                else:
                    score += 1.0
            score += len(CROSSES_BY_CELL[cell]) * 0.01  # centrality tiebreak
            if best_score is None or score > best_score:
                best_score = score
                best_move = cell
        return best_move


def ai_move(game, threshold=ENDGAME_THRESHOLD):
    ai = AI(threshold)
    return ai.choose(game)
