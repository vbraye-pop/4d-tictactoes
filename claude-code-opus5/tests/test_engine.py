"""The incremental search position must always agree with a direct scan."""

import random
import unittest

from fourd.board import O, X, other
from fourd.crosses import RULES_4D
from fourd.engine import Position
from tests.helpers import immediate_wins


def brute_force_threats(position: Position, player: str) -> set[int]:
    mine = position.boards[player]
    theirs = position.boards[other(player)]
    return set(immediate_wins(mine, mine | theirs))


class IncrementalState(unittest.TestCase):
    def test_threats_match_a_direct_scan_during_random_play(self):
        rng = random.Random(1234)
        for _ in range(40):
            position = Position()
            player = X
            for _ in range(rng.randint(0, 45)):
                cells = position.empty_cells()
                if not cells:
                    break
                position.make(rng.choice(cells), player)
                player = other(player)
                for side in (X, O):
                    self.assertEqual(set(position.winning_cells(side)),
                                     brute_force_threats(position, side))

    def test_make_and_unmake_restore_the_position_exactly(self):
        rng = random.Random(77)
        position = Position()
        played = []
        player = X
        for _ in range(30):
            cell = rng.choice(position.empty_cells())
            position.make(cell, player)
            played.append((cell, player))
            player = other(player)
        for cell, mover in reversed(played):
            position.unmake(cell, mover)
        self.assertEqual(position.boards, {X: 0, O: 0})
        self.assertEqual(position.occupied, 0)
        self.assertEqual(position.score, 0)
        self.assertEqual(position.count_x, [0] * len(RULES_4D.cross_masks))
        self.assertEqual(position.count_o, [0] * len(RULES_4D.cross_masks))
        self.assertEqual(position.threats, {X: {}, O: {}})

    def test_score_is_symmetric_between_the_players(self):
        rng = random.Random(5)
        cells = rng.sample(range(81), 12)
        mirrored = Position()
        straight = Position()
        for i, cell in enumerate(cells):
            straight.make(cell, X if i % 2 == 0 else O)
            mirrored.make(cell, O if i % 2 == 0 else X)
        self.assertEqual(straight.score, -mirrored.score)

    def test_building_from_masks_matches_playing_the_moves(self):
        rng = random.Random(88)
        x_cells = rng.sample(range(81), 8)
        o_cells = [c for c in rng.sample(range(81), 20) if c not in x_cells][:8]
        played = Position()
        for cell in x_cells:
            played.make(cell, X)
        for cell in o_cells:
            played.make(cell, O)
        built = Position(sum(1 << c for c in x_cells), sum(1 << c for c in o_cells))
        self.assertEqual(built.boards, played.boards)
        self.assertEqual(built.score, played.score)
        self.assertEqual(built.threats, played.threats)
        self.assertEqual(built.count_x, played.count_x)


if __name__ == "__main__":
    unittest.main()
