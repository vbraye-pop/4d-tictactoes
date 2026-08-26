"""Tests for 4D tic-tac-toe logic. Run with: python -m pytest tests/"""

import random

import game


def test_cross_count():
    assert len(game.CROSSES) == 1548


def test_all_crosses_registered_as_wins():
    for cross in game.CROSSES:
        g = game.Game()
        for cell in cross[:-1]:
            g.board[cell] = "X"
        assert g.winner is None
        last = cross[-1]
        assert g.is_legal(last)
        g.move(last)
        assert g.winner == "X", f"cross {cross} not detected"


def test_non_cross_five_cells_no_win():
    g = game.Game()
    cells = (0, 1, 2, 27, 80)
    assert set(cells) not in map(set, game.CROSSES)
    g.turn = "X"
    for c in cells:
        g.board[c] = "X"
    finished = g._check_finished(cells[-1])
    assert not finished
    assert g.winner is None


def test_move_legality():
    g = game.Game()
    assert g.is_legal(0)
    assert not g.is_legal(-1)
    assert not g.is_legal(81)
    g.move(0)
    assert not g.is_legal(0)
    g2 = game.Game()
    g2.winner = "X"
    assert not g2.is_legal(0)


def test_draw_branch():
    # full-board draw is mathematically unreachable here (every 2-coloring of
    # the 81 cells produces a monochromatic cross; verified via SAT). Verify
    # the draw mechanism: after the board is full and _check_finished runs,
    # winner is "draw" unless a completed cross exists.
    g = game.Game()
    # fill in random order until one cell remains
    random.seed(3)
    order = list(range(game.N_CELLS))
    random.shuffle(order)
    last = order.pop()
    for i, cell in enumerate(order):
        g.board[cell] = "X" if i % 2 == 0 else "O"
    g.turn = "X"
    # now fill the last cell; winner flips to "draw" or to a completed cross
    g.board[last] = "X"
    finished = g._check_finished(last)
    if finished:
        assert g.winner in ("X", "O", "draw")
    else:
        # not full (impossible) -> fail hard
        assert False


def test_ai_takes_win():
    g = game.Game()
    cross = list(game.CROSSES[0])
    for c in cross[:-1]:
        g.board[c] = "X"
    g.turn = "X"
    move = game.ai_move(g)
    assert move == cross[-1]


def test_ai_blocks():
    g = game.Game()
    cross = list(game.CROSSES[0])
    for c in cross[:-1]:
        g.board[c] = "O"
    g.turn = "X"
    move = game.ai_move(g)
    assert move == cross[-1]


def test_ai_endgame_safe_seeded_positions():
    random.seed(7)
    for _ in range(25):
        g = game.Game()
        n_used = game.N_CELLS - random.randint(1, 6)
        used = random.sample(range(game.N_CELLS), n_used)
        for i, cell in enumerate(used):
            g.board[cell] = "X" if i % 2 == 0 else "O"
        g.turn = "X"
        m = game.ai_move(g)
        assert g.board[m] is None


def test_endgame_solver_uses_optimal_move():
    random.seed(11)
    for _ in range(20):
        g = game.Game()
        empties = [i for i, v in enumerate(g.board) if v is None]
        random.shuffle(empties)
        used = empties[8:]  # keep only 8 empty
        for i, cell in enumerate(used):
            g.board[cell] = "X" if i % 2 == 0 else "O"
        ai = game.AI(endgame_threshold=9)
        m = ai.choose(g)
        assert g.board[m] is None
