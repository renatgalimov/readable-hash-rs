#!/usr/bin/env python3
"""Exhaustive reduced-model tests for the lenmin reference codec."""
import itertools
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lenmin  # noqa: E402

# Prefix-free rows; state 1 accepting-with-continuation, mixed lengths.
TOY = [
    (False, [("a", 1), ("bc", 3), ("d", 2), ("ef", 1)]),
    (True, [("x", 2), ("yy", 2)]),
    (True, [("z", 3)]),
    (True, []),
]


def brute_force(states, kmin, kmax):
    words = []

    def walk(state, text):
        if states[state][0] and text:
            words.append(text)
        for token, target in states[state][1]:
            walk(target, text + token)

    walk(0, "")
    phrases = []
    for k in range(kmin, kmax + 1):
        phrases += [" ".join(combo) for combo in itertools.product(words, repeat=k)]
    return words, phrases


class ToyTests(unittest.TestCase):
    def test_exhaustive(self):
        for kmin, kmax in ((1, 1), (2, 2), (3, 3), (1, 3), (2, 4)):
            words, phrases = brute_force(TOY, kmin, kmax)
            self.assertEqual(len(set(words)), len(words))
            model = lenmin.LenMin(kmin, kmax, TOY, limit=1)
            self.assertEqual(model.capacity, len(phrases))
            model.limit = model.capacity
            expected = sorted(phrases, key=lambda p: (len(p), p.count(" "), 0))
            by_length = [len(p) for p in expected]
            produced = [model.encode(v) for v in range(model.capacity)]
            self.assertEqual(sorted(produced), sorted(phrases))  # bijection onto all valid phrases
            self.assertEqual(len(set(produced)), len(produced))
            self.assertEqual([len(p) for p in produced], by_length)  # length-major
            for value, phrase in enumerate(produced):
                self.assertEqual(model.decode(phrase), value)
            for bad in ("", " ", "a ", " a", "a  a", "q", "ax x", "aa" * 7):
                self.assertTrue(model.decode(bad) is None or model.encode(model.decode(bad)) == bad)
            # every other string over a small alphabet decodes to None unless valid
            valid = set(produced)
            for size in range(1, 6):
                for combo in itertools.product("abcdefxyz ", repeat=size):
                    text = "".join(combo)
                    result = model.decode(text)
                    self.assertEqual(result is not None, text in valid, text)

    def test_truncated_limit(self):
        model = lenmin.LenMin(1, 2, TOY, limit=10)
        phrases = [model.encode(v) for v in range(10)]
        self.assertEqual(len(set(phrases)), 10)
        self.assertEqual(model.decode(model.encode(0)), 0)
        full = lenmin.LenMin(1, 2, TOY, limit=1)
        full.limit = full.capacity
        self.assertEqual([full.encode(v) for v in range(10)], phrases)
        self.assertIsNone(model.decode(full.encode(10)))

    def test_mix_is_bijection_samples(self):
        seen = set(lenmin.mix(v) for v in range(5000))
        self.assertEqual(len(seen), 5000)


if __name__ == "__main__":
    unittest.main()
