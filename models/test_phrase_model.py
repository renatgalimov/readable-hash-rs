import json
import unittest
from pathlib import Path

from compile_phrase import CONTEXTS, emitted, prefix_free, statistics, validate
from reversible_tables import choose_prefix_free

ROOT = Path(__file__).resolve().parent


class PhraseModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = json.loads((ROOT / "phrase_model.json").read_text())

    def test_all_rows_are_feasible_and_prefix_free(self):
        validate(self.model)
        self.assertEqual(len(CONTEXTS), 768)
        self.assertEqual(128 * 16 * 16 * 128, 1 << 22)
        self.assertEqual(128 * 16 * 8 * 128, 1 << 21)

    def test_duplicate_and_prefix_detected(self):
        self.assertFalse(prefix_free(["a", "ab"]))
        self.assertFalse(prefix_free(["ab", "ab"]))
        self.assertTrue(prefix_free(["ab", "ac"]))

    def test_local_prefix_conflict_is_optimized_at_full_capacity(self):
        choices = choose_prefix_free({"q": (100, 0), "qu": (7, 0), "qui": (6, 0), "a": (0, 9), "b": (0, 3)}, 3)
        self.assertEqual(choices, ("a", "b", "q"))
        # Local observations must be dropped when they would block capacity.
        self.assertEqual(choose_prefix_free({"a": (9, 0), "ab": (5, 0), "ac": (3, 0)}, 2), ("ab", "ac"))

    def test_report_lengths_and_path_counts(self):
        report = json.loads((ROOT / "phrase_report.json").read_text())["statistics"]
        self.assertEqual(report["word1"]["paths"], 1 << 22)
        self.assertEqual(report["word2_and_3"]["paths"], 1 << 21)
        self.assertEqual(report["phrase_min_letters"], report["word1"]["min_letters"] + 2 * report["word2_and_3"]["min_letters"])
        self.assertEqual(report["phrase_max_letters"], report["word1"]["max_letters"] + 2 * report["word2_and_3"]["max_letters"])
        self.assertEqual(report["spaces"], 2)

    def test_every_beginning_has_two_reachable_middle_and_ending_tables(self):
        indices = {context: index for index, context in enumerate(CONTEXTS)}
        for begin in self.model["begin"]:
            for middle in self.model["middle16"][indices[begin]]:
                for second in self.model["middle16"][indices[middle]]:
                    self.assertEqual(len(self.model["end128"][indices[second]]), 128)
                for second in self.model["middle8"][indices[middle]]:
                    self.assertEqual(len(self.model["end128"][indices[second]]), 128)


if __name__ == "__main__":
    unittest.main()
