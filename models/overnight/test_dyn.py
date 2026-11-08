"""Tests for the experimental dyn v1 compiler (run: python -m pytest models/overnight or python test_dyn.py)."""
import random
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import compile_dyn  # noqa: E402
import extract_counts  # noqa: E402
from report import TextModel  # noqa: E402

REPO = HERE.parent.parent
FROZEN = {"en-unique": ("en", "unique", 32), "en-fineweb": ("en", "fineweb-occ", 64), "tr-fineweb": ("tr", "fineweb-occ", 32)}


def reduced_states():
    end = compile_dyn.END

    def choice(text, target):
        return {"token": text, "text": text, "next": target, "fallback": False, "local": 1, "heldout": True}

    return [
        {"key": (0, None), "choices": [choice("ka", 1), choice("lo", 2), choice("m", end)]},
        {"key": (1, "ka"), "choices": [choice("ri", 2), choice("n", end), choice("sa", end)]},
        {"key": (2, "x"), "choices": [choice("t", end), choice("va", end)]},
    ]


class ReducedModel(unittest.TestCase):
    def test_exhaustive_bijection_23_words(self):
        codec = compile_dyn.Codec(reduced_states(), 23)  # 7^23 >= 2^64
        words = [codec.word(rank)[0] for rank in range(codec.width)]
        self.assertEqual(words, ["karit", "kariva", "kan", "kasa", "lot", "lova", "m"])
        self.assertEqual(len(set(words)), 7)
        for rank, word in enumerate(words):
            self.assertEqual(codec.parse_word(word), rank)
            for end in range(len(word)):
                self.assertIsNone(codec.parse_word(word[:end]))
        for value in [0, 1, 2, 42, 2**63 - 1, 2**63, 2**64 - 2, 2**64 - 1]:
            self.assertEqual(codec.decode(codec.encode(value)), value)
        self.assertIsNone(codec.decode(" ".join([words[-1]] * 23)))  # rank >= 2^64

    def test_exact_metrics_mass(self):
        codec = compile_dyn.Codec(reduced_states(), 23)
        for spans in compile_dyn.word_weights(codec):
            total = sum(limit * multiplicity for limit, multiplicity in spans)
            self.assertEqual(total, 2**64)
        compile_dyn.exact_metrics(codec)  # asserts histogram mass == 2^64 internally

    def test_insufficient_capacity_rejected(self):
        with self.assertRaises(ValueError):
            compile_dyn.Codec(reduced_states(), 22)


class TurkishText(unittest.TestCase):
    def test_turkish_casing(self):
        self.assertEqual(extract_counts.lower("IŞIK İSTANBUL Ilık", "tr"), "ışık istanbul ılık")
        self.assertEqual(extract_counts.lower("India", "en"), "india")


class FrozenModels(unittest.TestCase):
    def test_structure_and_roundtrip(self):
        rng = random.Random(5)
        for stem in FROZEN:
            model = TextModel(REPO / "src/dyn_models" / f"{stem}.txt")  # asserts prefix-free
            self.assertGreaterEqual(model.width ** model.words, 2**64)
            for index, row in enumerate(model.states):
                self.assertTrue(all(target is None or target > index for _, target in row))
            codec = compile_dyn.Codec([{"choices": [{"text": text, "next": compile_dyn.END if target is None else target}
                                                    for text, target in row]} for row in model.states], model.words)
            for value in [0, 1, 2**64 - 1] + [rng.getrandbits(64) for _ in range(3000)]:
                phrase = model.encode(value)
                self.assertEqual(codec.decode(phrase), value)
                self.assertIsNone(codec.decode(phrase + " "))
                self.assertIsNone(codec.decode(phrase.replace(" ", "", 1)))

    @unittest.skipUnless((compile_dyn.CORPORA / "en_counts.json.gz").exists(), "corpus counts absent")
    def test_frozen_models_reproduce(self):
        for stem, (language, source, cap) in FROZEN.items():
            states, _, _ = compile_dyn.compile_arm(language, source, cap, 2, 3, 5, 2)
            name = f"{language}-{source}-cap{cap}-t5-w3"
            self.assertEqual(compile_dyn.export_text(states, name, 3),
                             (REPO / "src/dyn_models" / f"{stem}.txt").read_text(encoding="utf-8"), stem)


if __name__ == "__main__":
    unittest.main()
