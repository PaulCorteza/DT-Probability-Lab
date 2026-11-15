import unittest

from dice_engine import is_success, probability_for_keep, best_strategy


class DiceEngineTests(unittest.TestCase):
    def test_three_of_a_kind(self):
        self.assertTrue(is_success([2, 2, 2, 4, 5], "Three of a kind"))
        self.assertFalse(is_success([2, 2, 3, 4, 5], "Three of a kind"))

    def test_four_sixes(self):
        self.assertTrue(is_success([6, 6, 6, 6, 2], "At least four sixes"))
        self.assertFalse(is_success([6, 6, 6, 2, 2], "At least four sixes"))

    def test_straights(self):
        self.assertTrue(is_success([1, 2, 3, 4, 5], "Small straight (1–5)"))
        self.assertTrue(is_success([2, 3, 4, 5, 6], "Large straight (2–6)"))

    def test_keep_all_successful_roll(self):
        roll = [3, 3, 3, 2, 5]
        self.assertEqual(
            probability_for_keep(roll, [0, 1, 2, 3, 4], "Three of a kind"),
            1.0,
        )

    def test_best_strategy_probability_is_valid(self):
        keep, probability = best_strategy([1, 1, 2, 4, 5], "Three of a kind")
        self.assertGreaterEqual(probability, 0.0)
        self.assertLessEqual(probability, 1.0)


if __name__ == "__main__":
    unittest.main()
