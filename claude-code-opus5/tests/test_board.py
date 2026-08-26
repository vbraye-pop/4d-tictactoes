"""Move legality, win detection and draw detection."""

import random
import unittest

from fourd.board import (DRAW, ONGOING, O, WIN, X, Game, IllegalMove,
                         find_winning_cross, winning_cross_through)
from fourd.crosses import RULES_4D, build_rules
from tests.helpers import masks, quiet_filler

RULES_2D = build_rules(2)


class MoveLegality(unittest.TestCase):
    def test_x_moves_first_and_players_alternate(self):
        game = Game()
        self.assertEqual(game.to_move, X)
        game.play(0)
        self.assertEqual(game.to_move, O)
        game.play(1)
        self.assertEqual(game.to_move, X)

    def test_occupied_cells_are_rejected(self):
        game = Game()
        game.play(40)
        self.assertFalse(game.is_legal(40))
        with self.assertRaises(IllegalMove):
            game.play(40)
        self.assertEqual(game.to_move, O)
        self.assertEqual(game.move_count, 1)

    def test_cells_outside_the_board_are_rejected(self):
        game = Game()
        for cell in (-1, 81, 1000):
            self.assertFalse(game.is_legal(cell))
            with self.assertRaises(IllegalMove):
                game.play(cell)

    def test_every_empty_cell_is_legal(self):
        game = Game()
        game.play(40)
        legal = [cell for cell in range(81) if game.is_legal(cell)]
        self.assertEqual(legal, [cell for cell in range(81) if cell != 40])

    def test_no_move_is_legal_once_the_game_is_over(self):
        cross = RULES_4D.cross_cells[0]
        others = quiet_filler(set(cross), 4)
        game = Game.from_cells(list(cross[:4]), others, to_move=X)
        game.play(cross[4])
        self.assertEqual(game.status, WIN)
        self.assertFalse(any(game.is_legal(cell) for cell in range(81)))
        with self.assertRaises(IllegalMove):
            game.play(next(c for c in range(81) if game.owner(c) is None))

    def test_from_cells_rejects_overlapping_marks(self):
        with self.assertRaises(IllegalMove):
            Game.from_cells([1, 2], [2, 3])


class WinDetection(unittest.TestCase):
    def test_every_one_of_the_1548_crosses_wins_when_completed(self):
        for cross in RULES_4D.cross_cells:
            filler = quiet_filler(set(cross), 4)
            game = Game.from_cells(list(cross[:4]), filler, to_move=X)
            self.assertEqual(game.status, ONGOING)
            game.play(cross[4])
            self.assertEqual(game.status, WIN)
            self.assertEqual(game.winner, X)
            self.assertEqual(set(game.winning_cross), set(cross))

    def test_o_can_win_too(self):
        cross = RULES_4D.cross_cells[700]
        filler = quiet_filler(set(cross), 5)
        game = Game.from_cells(filler, list(cross[:4]), to_move=O)
        game.play(cross[4])
        self.assertEqual(game.winner, O)
        self.assertEqual(set(game.winning_cross), set(cross))

    def test_five_cells_that_are_not_a_cross_do_not_win(self):
        crosses = {frozenset(cross) for cross in RULES_4D.cross_cells}
        rng = random.Random(20240707)
        checked = 0
        while checked < 3000:
            cells = frozenset(rng.sample(range(81), 5))
            if cells in crosses:
                continue
            checked += 1
            x_mask, _ = masks(cells, [])
            self.assertIsNone(find_winning_cross(RULES_4D, x_mask))

    def test_near_miss_shapes_do_not_win(self):
        near_misses = [
            [0, 1, 2, 3, 4],                      # five cells in a row is not a cross
            [40, 13, 67, 4, 5],                   # a line plus two unrelated cells
            [40, 13, 67, 39, 42],                 # a cross with one arm cell moved
            [0, 27, 54, 1, 28],                   # a full line plus part of another
        ]
        for cells in near_misses:
            x_mask, _ = masks(cells, [])
            self.assertIsNone(find_winning_cross(RULES_4D, x_mask), cells)

    def test_four_of_a_cross_is_not_a_win(self):
        for cross in RULES_4D.cross_cells[::37]:
            x_mask, _ = masks(cross[:4], [])
            self.assertIsNone(find_winning_cross(RULES_4D, x_mask))

    def test_incremental_and_global_detection_agree(self):
        rng = random.Random(4242)
        for _ in range(400):
            cells = rng.sample(range(81), rng.randint(1, 30))
            x_mask, _ = masks(cells, [])
            last = cells[-1]
            through = winning_cross_through(RULES_4D, x_mask, last)
            overall = find_winning_cross(RULES_4D, x_mask)
            if through is not None:
                self.assertIsNotNone(overall)
            else:
                # a cross not passing through the last cell would already have
                # ended the game earlier, so the global scan is the authority
                self.assertTrue(overall is None or last not in overall)

    def test_a_cross_is_detected_from_any_completion_order(self):
        rng = random.Random(9)
        cross = list(RULES_4D.cross_cells[123])
        for _ in range(20):
            order = cross[:]
            rng.shuffle(order)
            filler = quiet_filler(set(cross), 4)
            game = Game.from_cells(order[:4], filler, to_move=X)
            self.assertEqual(game.status, ONGOING)
            game.play(order[4])
            self.assertEqual(set(game.winning_cross), set(cross))


class DrawDetection(unittest.TestCase):
    """Draws are impossible in 4D, so the two-dimensional rules exercise them."""

    def test_two_dimensional_game_can_end_in_a_draw(self):
        x_cells = [4, 0, 1, 2, 3]
        o_cells = [8, 7, 6, 5]
        game = Game(rules=RULES_2D)
        for step, cell in enumerate([4, 8, 0, 7, 1, 6, 2, 5, 3]):
            self.assertEqual(game.status, ONGOING)
            game.play(cell)
        self.assertEqual(game.status, DRAW)
        self.assertIsNone(game.winner)
        self.assertIsNone(game.winning_cross)
        self.assertEqual(sorted(c for c in range(9) if game.owner(c) == X), sorted(x_cells))
        self.assertEqual(sorted(c for c in range(9) if game.owner(c) == O), sorted(o_cells))

    def test_a_full_two_dimensional_board_with_a_cross_is_a_win_not_a_draw(self):
        game = Game(rules=RULES_2D)
        for cell in [4, 0, 1, 2, 7, 6, 3, 8, 5]:
            game.play(cell)
        self.assertEqual(game.status, WIN)
        self.assertEqual(game.winner, X)
        self.assertEqual(set(game.winning_cross), {4, 1, 7, 3, 5})

    def test_no_move_is_legal_after_a_draw(self):
        game = Game(rules=RULES_2D)
        for cell in [4, 8, 0, 7, 1, 6, 2, 5, 3]:
            game.play(cell)
        with self.assertRaises(IllegalMove):
            game.play(0)

    def test_the_four_dimensional_game_always_produces_a_winner(self):
        """Every filled 3^4 board contains a cross, so play never runs out."""
        rng = random.Random(31337)
        for _ in range(25):
            game = Game()
            while game.status == ONGOING:
                game.play(rng.choice(game.empty_cells))
            self.assertEqual(game.status, WIN)
            self.assertLess(game.move_count, 81)
            self.assertIsNotNone(game.winning_cross)
            mask = game.boards[game.winner]
            for cell in game.winning_cross:
                self.assertTrue(mask >> cell & 1)


if __name__ == "__main__":
    unittest.main()
