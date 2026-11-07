import unittest

from reversible_tables import choose_prefix_free


class PrefixFreeSelectionTests(unittest.TestCase):
    def test_training_counts_match_checked_in_model(self):
        from reversible_tables import load_training_counts
        from pathlib import Path

        root = Path(__file__).parent
        counts = load_training_counts(root / "training-data/english-lowercase.txt",
                                      root / "training-data/english-lowercase-model.json")
        self.assertEqual(counts["word_count"], 94080)
        self.assertGreater(sum(counts["begin"].values()), 0)
        self.assertGreater(sum(sum(row.values()) for row in counts["middle"].values()), 0)

    def test_prefers_local_weight_then_global_weight(self):
        candidates = {"a": (5, 100), "ab": (4, 0), "ac": (4, 0), "b": (0, 7)}
        self.assertEqual(choose_prefix_free(candidates, 2), ("ab", "ac"))

    def test_matches_exhaustive_search(self):
        from itertools import combinations

        candidates = {"a": (4, 2), "ab": (3, 7), "ac": (3, 1),
                      "b": (2, 9), "bc": (2, 10), "c": (1, 2)}
        for size in range(1, 5):
            valid = [choice for choice in combinations(sorted(candidates), size)
                     if not any(second.startswith(first) for first, second in combinations(choice, 2))]
            if not valid:
                with self.assertRaises(ValueError):
                    choose_prefix_free(candidates, size)
                continue
            expected = min(valid, key=lambda choice: (
                -sum(candidates[token][0] for token in choice),
                -sum(candidates[token][1] for token in choice), choice))
            self.assertEqual(choose_prefix_free(candidates, size), expected)

    def test_reports_insufficient_capacity(self):
        with self.assertRaises(ValueError):
            choose_prefix_free({"a": (1, 0), "ab": (2, 0)}, 2)

    def test_lexical_tie_break(self):
        self.assertEqual(choose_prefix_free({"aa": (1, 0), "ab": (1, 0)}, 1), ("aa",))

    def test_length_dp_matches_brute_force_small_domain(self):
        from reversible_metrics import lengths

        tokens = ["a"] * 1024
        tokens[0:2] = ["^a", "^abc"]
        for index in range(32):
            tokens[512 + index] = "a" * (1 + index % 5)
        for index in range(16):
            tokens[256 + index] = "a" * (1 + index % 3) + "$"
        beginning = [0, 1]
        rows = {"middle": [list(range(512, 544)) for _ in range(768)],
                "end": [list(range(256, 272)) for _ in range(768)]}
        actual = []
        for value in range(256):
            quotient, begin = divmod(value, len(beginning))
            size = len(tokens[beginning[begin]]) - 1
            for _ in range(11):
                size += len(tokens[512 + quotient % 32])
                quotient //= 32
            size += len(tokens[256 + quotient]) - 1
            actual.append(size)
        self.assertEqual(lengths(beginning, rows, tokens, True, maximum=255),
                         (min(actual), max(actual)))


if __name__ == "__main__":
    unittest.main()
