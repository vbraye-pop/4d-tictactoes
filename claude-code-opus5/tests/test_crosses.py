"""The winning-cross geometry."""

import unittest
from itertools import combinations

from fourd.crosses import RULES_4D, build_rules
from tests.helpers import crosses_from_definition


class CrossGeometry(unittest.TestCase):
    def test_there_are_exactly_1548_crosses_in_four_dimensions(self):
        self.assertEqual(len(RULES_4D.cross_cells), 1548)

    def test_every_cross_has_five_distinct_cells(self):
        for cross in RULES_4D.cross_cells:
            self.assertEqual(len(set(cross)), 5)

    def test_generated_crosses_match_the_definition(self):
        derived = crosses_from_definition(4)
        generated = {frozenset(RULES_4D.coords(cell) for cell in cross)
                     for cross in RULES_4D.cross_cells}
        self.assertEqual(generated, derived)

    def test_two_dimensional_board_has_the_six_expected_shapes(self):
        rules = build_rules(2)
        self.assertEqual(len(rules.cross_cells), 6)
        shapes = {frozenset(rules.coords(cell) for cell in cross)
                  for cross in rules.cross_cells}
        plus = frozenset({(1, 1), (0, 1), (2, 1), (1, 0), (1, 2)})
        ex = frozenset({(1, 1), (0, 0), (2, 2), (0, 2), (2, 0)})
        self.assertIn(plus, shapes)
        self.assertIn(ex, shapes)
        for shape in shapes:
            self.assertIn((1, 1), shape)

    def test_three_dimensional_count_is_consistent_with_the_geometry(self):
        rules = build_rules(3)
        self.assertEqual(len(rules.cross_cells), len(crosses_from_definition(3)))

    def test_cell_index_and_coordinates_round_trip(self):
        for cell in range(RULES_4D.cell_count):
            self.assertEqual(RULES_4D.index(RULES_4D.coords(cell)), cell)

    def test_cross_index_per_cell_is_consistent(self):
        for cell in range(RULES_4D.cell_count):
            for cross_index in RULES_4D.cell_crosses[cell]:
                self.assertIn(cell, RULES_4D.cross_cells[cross_index])
        total = sum(len(entry) for entry in RULES_4D.cell_crosses)
        self.assertEqual(total, 5 * len(RULES_4D.cross_cells))

    def test_masks_agree_with_cell_lists(self):
        for cross, mask in zip(RULES_4D.cross_cells, RULES_4D.cross_masks):
            self.assertEqual(mask, sum(1 << cell for cell in cross))

    def test_no_cross_contains_another(self):
        for a, b in combinations(RULES_4D.cross_cells[:300], 2):
            self.assertFalse(set(a) <= set(b))


if __name__ == "__main__":
    unittest.main()
