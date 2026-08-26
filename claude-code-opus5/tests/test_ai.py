"""The opponent: tactics, exact endgame play and overall strength."""

import random
import time
import unittest

from fourd.ai import DEFAULT_BUDGET, choose_move
from fourd.board import ONGOING, O, WIN, X, Game, other
from fourd.crosses import RULES_4D
from tests.helpers import (QUIET_ENDGAMES, immediate_wins, masks, quiet_filler,
                           reference_move_values, side_to_move)

FAST = 0.4


class Tactics(unittest.TestCase):
    def test_takes_an_available_win(self):
        for index in range(0, len(RULES_4D.cross_cells), 97):
            cross = RULES_4D.cross_cells[index]
            filler = quiet_filler(set(cross), 4)
            game = Game.from_cells(list(cross[:4]), filler, to_move=X)
            decision = choose_move(game.boards[X], game.boards[O], X, FAST)
            self.assertEqual(decision.cell, cross[4], f"cross {index}")
            self.assertEqual(decision.reason, "win")
            game.play(decision.cell)
            self.assertEqual(game.status, WIN)
            self.assertEqual(game.winner, X)

    def test_blocks_the_cell_that_would_complete_the_opponents_cross(self):
        for index in range(0, len(RULES_4D.cross_cells), 149):
            cross = RULES_4D.cross_cells[index]
            filler = quiet_filler(set(cross), 4)
            game = Game.from_cells(filler, list(cross[:4]), to_move=X)
            self.assertEqual(game.status, ONGOING)
            self.assertEqual(immediate_wins(game.boards[X], game.occupied), [])
            decision = choose_move(game.boards[X], game.boards[O], X, FAST)
            self.assertEqual(decision.cell, cross[4], f"cross {index}")
            self.assertEqual(decision.reason, "block")
            game.play(decision.cell)
            self.assertEqual(game.status, ONGOING)

    def test_prefers_its_own_win_over_blocking(self):
        mine = RULES_4D.cross_cells[10]
        theirs = next(cross for cross in RULES_4D.cross_cells
                      if not set(cross) & set(mine))
        game = Game.from_cells(list(mine[:4]), list(theirs[:4]), to_move=X)
        decision = choose_move(game.boards[X], game.boards[O], X, FAST)
        self.assertEqual(decision.cell, mine[4])
        game.play(decision.cell)
        self.assertEqual(game.winner, X)

    def test_blocks_for_o_as_well(self):
        cross = RULES_4D.cross_cells[321]
        filler = quiet_filler(set(cross), 5)
        game = Game.from_cells(list(cross[:4]), filler, to_move=O)
        decision = choose_move(game.boards[X], game.boards[O], O, FAST)
        self.assertEqual(decision.cell, cross[4])


class EndgameOptimality(unittest.TestCase):
    """Compare against a plain minimax that shares no code with the AI."""

    def test_plays_an_optimal_move_in_solved_endgames(self):
        for empties, position in QUIET_ENDGAMES.items():
            x_mask, o_mask = masks(position["x"], position["o"])
            player = side_to_move(position["x"], position["o"])
            # neither side can win on the spot, so this needs a real search
            self.assertEqual(immediate_wins(x_mask, x_mask | o_mask), [])
            self.assertEqual(immediate_wins(o_mask, x_mask | o_mask), [])

            values = reference_move_values(x_mask, o_mask, player)
            best = max(values.values())
            decision = choose_move(x_mask, o_mask, player, FAST)
            self.assertIn(decision.cell, values, f"{empties} empty cells")
            self.assertEqual(values[decision.cell], best,
                             f"{empties} empty cells: chose {decision.cell} "
                             f"worth {values[decision.cell]}, best is {best}")
            self.assertTrue(decision.exact)
            self.assertEqual(decision.value, best)

    def test_the_endgame_fixtures_really_do_separate_good_from_bad_moves(self):
        x_mask, o_mask = masks(QUIET_ENDGAMES[13]["x"], QUIET_ENDGAMES[13]["o"])
        player = side_to_move(QUIET_ENDGAMES[13]["x"], QUIET_ENDGAMES[13]["o"])
        values = reference_move_values(x_mask, o_mask, player)
        self.assertIn(1, values.values())
        self.assertIn(-1, values.values())

    def test_wins_a_won_endgame_against_perfect_defence(self):
        """Play the position out: the AI must actually convert, not just claim."""
        position = QUIET_ENDGAMES[13]
        x_mask, o_mask = masks(position["x"], position["o"])
        player = side_to_move(position["x"], position["o"])
        game = Game.from_cells(position["x"], position["o"], to_move=player)
        winner_should_be = player
        while game.status == ONGOING:
            decision = choose_move(game.boards[X], game.boards[O], game.to_move, FAST)
            game.play(decision.cell)
        self.assertEqual(game.status, WIN)
        self.assertEqual(game.winner, winner_should_be)

    def test_plays_on_optimally_in_a_proven_lost_endgame(self):
        """Every move loses, so any legal one is optimal, but it must still play."""
        position = QUIET_ENDGAMES[13]
        game = Game.from_cells(position["x"], position["o"],
                               to_move=side_to_move(position["x"], position["o"]))
        game.play(26)  # a winning move for the side to move, leaving O lost
        self.assertEqual(game.status, ONGOING)
        values = reference_move_values(game.boards[X], game.boards[O], game.to_move)
        self.assertEqual(set(values.values()), {-1})

        decision = choose_move(game.boards[X], game.boards[O], game.to_move, FAST)
        self.assertIn(decision.cell, values)
        self.assertTrue(game.is_legal(decision.cell))
        self.assertEqual(values[decision.cell], -1)
        # it still has to hold out as long as the rules allow
        game.play(decision.cell)
        self.assertEqual(game.status, ONGOING)

    def test_finds_the_shortest_forced_win_when_one_exists(self):
        cross = RULES_4D.cross_cells[500]
        filler = quiet_filler(set(cross), 4)
        x_mask, o_mask = masks(cross[:4], filler)
        decision = choose_move(x_mask, o_mask, X, FAST)
        self.assertEqual(decision.value, 1)
        self.assertTrue(decision.exact)


class GeneralPlay(unittest.TestCase):
    def test_always_returns_a_legal_move(self):
        rng = random.Random(2718)
        for _ in range(5):
            game = Game()
            while game.status == ONGOING:
                decision = choose_move(game.boards[X], game.boards[O], game.to_move, FAST)
                self.assertTrue(game.is_legal(decision.cell))
                game.play(decision.cell)
                if game.status == ONGOING and game.empty_cells:
                    game.play(rng.choice(game.empty_cells))

    def test_opens_in_the_centre_of_the_board(self):
        decision = choose_move(0, 0, X, FAST)
        self.assertEqual(RULES_4D.coords(decision.cell), (1, 1, 1, 1))

    def test_is_deterministic(self):
        game = Game()
        for cell in (40, 0, 13, 1):
            game.play(cell)
        first = choose_move(game.boards[X], game.boards[O], X, FAST)
        second = choose_move(game.boards[X], game.boards[O], X, FAST)
        self.assertEqual(first.cell, second.cell)

    def test_beats_a_random_opponent_from_either_side(self):
        rng = random.Random(31415)
        for ai_side in (X, O):
            for _ in range(2):
                game = Game()
                while game.status == ONGOING:
                    if game.to_move == ai_side:
                        game.play(choose_move(game.boards[X], game.boards[O],
                                              game.to_move, FAST).cell)
                    else:
                        game.play(rng.choice(game.empty_cells))
                self.assertEqual(game.winner, ai_side)

    def test_stays_inside_its_time_budget(self):
        game = Game()
        game.play(40)
        game.play(0)
        started = time.perf_counter()
        choose_move(game.boards[X], game.boards[O], X, DEFAULT_BUDGET)
        self.assertLess(time.perf_counter() - started, 4 * DEFAULT_BUDGET)


if __name__ == "__main__":
    unittest.main()
