import json
import unittest
from pathlib import Path

import compile_phrase as v5

ROOT = Path(__file__).resolve().parent


def decode(model, phrase):
    """Reference decoder: find the one matching token at each point (rows are prefix-free together)."""
    text = [v5.text_of(token) for token in model["tokens"]]
    words = phrase.split(" ")
    if len(words) not in (3, 4):
        return None
    value, offset, lengths = 0, 5, []

    def take(rest, row):
        matches = [(digit, token) for digit, token in enumerate(row) if rest.startswith(text[token])]
        assert len(matches) <= 1
        return matches[0] if matches else None

    for position, word in enumerate(words):
        found = take(word, model["begin"])
        if not found:
            return None
        digit, token = found
        rest, middles = word[len(text[token]):], 0
        value, offset = value | digit << offset, offset + 7
        width = v5.ending_width(len(words), position)
        while True:
            row = (model["end32"] if width == 5 else model["end16"])[v5.context(token)]
            found = take(rest, row)
            if found:
                digit, end = found
                rest = rest[len(text[end]):]
                value, offset = value | digit << offset, offset + width
                break
            found = take(rest, model["middle"][v5.context(token)]) if middles < 3 else None
            if not found:
                return None
            digit, token = found
            rest, middles = rest[len(text[token]):], middles + 1
            value, offset = value | digit << offset, offset + 5
        if rest:
            return None
        lengths.append(middles + 2)
    layouts = v5.layouts()
    if tuple(lengths) not in layouts:
        return None
    return value | layouts.index(tuple(lengths))


class PhraseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = json.loads((ROOT / "phrase_model.json").read_text())

    def test_checked_in_files_match_the_compiler(self):
        model, report = v5.compile_model()
        self.assertEqual(model, self.model)
        self.assertEqual(report, json.loads((ROOT / "phrase_report.json").read_text()))
        self.assertEqual((ROOT.parent / "src" / "phrase_data.rs").read_text(), v5.rust_source(model))

    def test_tables_have_no_single_letters_and_decode_by_letters(self):
        v5.validate(self.model)  # 2+ letters, beginnings prefix-free, middles + endings prefix-free per context

    def test_every_layout_is_64_bits(self):
        layouts = v5.layouts()
        self.assertEqual(len(layouts), 32)
        self.assertEqual(sum(len(layout) == 3 for layout in layouts), 12)
        for layout in layouts:
            bits = 5 + sum(7 + 5 * (length - 2) + v5.ending_width(len(layout), position)
                           for position, length in enumerate(layout))
            self.assertEqual(bits, 64, layout)

    def test_reference_roundtrip(self):
        state = 0x243F6A8885A308D3
        for _ in range(20_000):
            state = (state * 6364136223846793005 + 1442695040888963407) % (1 << 64)
            phrase = v5.encode(self.model, state)
            self.assertEqual(decode(self.model, phrase), state, phrase)
            self.assertTrue(all(v5.has_vowel(word) for word in phrase.split()), phrase)
        self.assertEqual(v5.encode(self.model, 0x243F6A8885A308D3), "bongere siuninut nuunamus")


if __name__ == "__main__":
    unittest.main()
