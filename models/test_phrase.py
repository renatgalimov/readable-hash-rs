import json
import unittest
from pathlib import Path

import compile_phrase as phrase

ROOT = Path(__file__).resolve().parent


def decode(model, phrase_text):
    """Reference decoder: find the one matching token at each point (rows are prefix-free together)."""
    text = [phrase.text_of(token) for token in model["tokens"]]
    words = phrase_text.split(" ")
    if len(words) not in (3, 4):
        return None
    value, offset, lengths = 0, phrase.layout_bits(), []

    def take(rest, row):
        matches = [(digit, token) for digit, token in enumerate(row) if rest.startswith(text[token])]
        assert len(matches) <= 1
        return matches[0] if matches else None

    for word in words:
        found = take(word, model["begin"])
        if not found:
            return None
        digit, token = found
        rest, middles = word[len(text[token]):], 0
        value, offset = value | digit << offset, offset + phrase.BEGIN_SIZE.bit_length() - 1
        while True:
            found = take(rest, model["end32"][phrase.context(token)])
            if found:
                digit, end = found
                rest = rest[len(text[end]):]
                value, offset = value | digit << offset, offset + phrase.END_SIZE.bit_length() - 1
                break
            found = take(rest, model["middle"][phrase.context(token)]) if middles < phrase.MAX_WORD - 2 else None
            if not found:
                return None
            digit, token = found
            rest, middles = rest[len(text[token]):], middles + 1
            value, offset = value | digit << offset, offset + phrase.MIDDLE_SIZE.bit_length() - 1
        if rest:
            return None
        lengths.append(middles + 2)
    layouts = phrase.layouts()
    if tuple(lengths) not in layouts:
        return None
    return value | layouts.index(tuple(lengths))


class PhraseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = json.loads((ROOT / "phrase_model.json").read_text())

    def test_checked_in_files_match_the_compiler(self):
        model, report = phrase.compile_model()
        self.assertEqual(model, self.model)
        self.assertEqual(report, json.loads((ROOT / "phrase_report.json").read_text()))
        self.assertEqual((ROOT.parent / "src" / "phrase_data.rs").read_text(), phrase.rust_source(model))

    def test_tables_have_no_single_letters_and_decode_by_letters(self):
        phrase.validate(self.model)  # 2+ letters, beginnings prefix-free, middles + endings prefix-free per context

    def test_every_layout_is_64_bits(self):
        layouts = phrase.layouts()
        self.assertEqual(len(layouts), 16)
        self.assertEqual(sum(len(layout) == 3 for layout in layouts), 6)
        bits = {kind: size.bit_length() - 1 for kind, size in
                (("b", phrase.BEGIN_SIZE), ("m", phrase.MIDDLE_SIZE), ("e", phrase.END_SIZE))}
        for layout in layouts:
            total = phrase.layout_bits() + sum(bits["b"] + bits["m"] * (length - 2) + bits["e"] for length in layout)
            self.assertEqual(total, 64, layout)

    def test_reference_roundtrip(self):
        state = 0x243F6A8885A308D3
        for _ in range(20_000):
            state = (state * 6364136223846793005 + 1442695040888963407) % (1 << 64)
            text = phrase.encode(self.model, state)
            self.assertEqual(decode(self.model, text), state, text)
            self.assertTrue(all(phrase.has_vowel(word) for word in text.split()), text)
        self.assertEqual(phrase.encode(self.model, 0x243F6A8885A308D3), "sain aralin suus umadde")


if __name__ == "__main__":
    unittest.main()
