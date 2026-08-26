"""Tests for the server game object (state machine and state serialization)."""

import time

import pytest

from game import O, X, idx_of
from server import AI_DELAY_SECONDS, Game


@pytest.fixture()
def game():
    g = Game()
    g.new_game("pvp")
    return g


def test_new_game_modes():
    g = Game()
    s = g.new_game("ai")
    assert s["mode"] == "ai"
    assert s["to_move"] == X
    assert s["winner"] is None
    s2 = g.new_game("pvp")
    assert s2["mode"] == "pvp"
    assert s2["cells"] == ["."] * 81
    assert s["move_count"] == 0
    assert s["cells"] == ["."] * 81


def test_move_flow_and_rejections(game):
    state, err = game.human_move(40)
    assert err is None
    assert state["cells"][40] == "X"
    assert state["to_move"] == O
    state, err = game.human_move(40)
    assert err is not None  # occupied
    state, err = game.human_move(81)
    assert err is not None  # out of range
    state, err = game.human_move(3.5)
    assert err is not None  # not an integer
    state, err = game.human_move(31)
    assert err is None
    assert state["cells"][31] == "O"
    assert state["last_move"] == 31
    assert state["move_count"] == 2


def test_winning_cross_payload(game):
    # X completes the plus cross through the center on move 9.
    seq = [40, 0, 39, 2, 41, 6, 37, 8, 43]
    for cell in seq:
        state, err = game.human_move(cell)
        assert err is None
    assert state["winner"] == X
    assert state["winning_cross"] is not None
    wc = state["winning_cross"]
    assert sorted(wc["cells"]) == sorted([40, 39, 41, 37, 43])
    assert wc["center"] == 40
    assert set(wc["line_labels"]) == {"X axis", "Y axis"}
    assert wc["slice_counts"] == {"0": 0, "1": 5, "2": 0}
    # board is locked: further moves rejected
    state, err = game.human_move(20)
    assert err is not None


def test_ai_mode_flow():
    g = Game()
    g.new_game("ai")
    state, err = g.human_move(40)  # human is X
    assert err is None
    assert state["ai_pending"] is True
    assert state["to_move"] == O
    # human cannot move while the AI is thinking
    state, err = g.human_move(31)
    assert err is not None
    # the AI answers within the bounded delay
    deadline = time.monotonic() + AI_DELAY_SECONDS + 5
    while g.state()["ai_pending"] and time.monotonic() < deadline:
        time.sleep(0.05)
    s = g.state()
    assert s["ai_pending"] is False
    assert s["move_count"] == 2
    assert s["to_move"] == X
    assert s["cells"].count("X") == 1
    assert s["cells"].count("O") == 1


def test_ai_mode_new_game_cancels_pending_move():
    g = Game()
    g.new_game("ai")
    state, _ = g.human_move(40)
    assert state["ai_pending"] is True
    # a new game started while the AI thinks must cancel the old AI move
    g.new_game("pvp")
    time.sleep(AI_DELAY_SECONDS + 0.3)
    s = g.state()
    assert s["mode"] == "pvp"
    assert s["move_count"] == 0
    assert s["ai_pending"] is False


def test_draw_state_serialization():
    g = Game()
    g.new_game("pvp")
    # white-box: a full board with no winner is a draw by rule
    for i in range(81):
        bit = 1 << i
        if i % 2 == 0:
            g.board.x |= bit
        else:
            g.board.o |= bit
    s = g.state()
    assert s["draw"] is True
    assert s["winner"] is None
    state, err = g.human_move(0)
    assert err is not None  # board full and over
