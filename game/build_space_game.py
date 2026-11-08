"""Build renatgalimov/blog/static/diagrams/space-game.html from space-game.template.html.

Beginnings come from the frozen phrase_v5 model; the middle and ending pools are still the game's fixed lists.
"""
import collections
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "models"))
import compile_phrase_v5 as v5  # noqa: E402

V5_MODEL = HERE.parent / "models/phrase_v5_model.json"
MODEL = HERE.parent / "models/phrase_v3_model.json"
ENGLISH = HERE.parent / "models/training-data/english-lowercase.txt"
OUT = Path("/home/agent/projects/renatgalimov/blog/static/diagrams/space-game.html")
WORDS = sorted(
    "at by if in is my no of on or so to up we "
    "the and for but not our his her its all any few one two ten new old big".split()
)
# 32 middles: the model's 32 most frequent, with "l" swapped for "bi" ("l"+"es" spelled the same as "le"+"s").
MIDDLES = sorted("ba bi bo ce ci ck di do ff ga k le li lo ma mi mo ne ni ra re ri ro se si ti ur vi w x y z".split())
# 32 endings that look like English word endings (picked from the model's ending tokens).
ENDINGS = sorted(
    "ing ed er es ly al ion ous ble ic an en on ness y s "
    "ation le ling ll man ns re rs ry te ted th ting ts um ve".split()
)
BEGIN_COUNT = 128
MAX_MIDDLES = 3  # a built word has at most 5 tokens


def assert_decodable(begin):
    """Different picks must spell different words, or a word would store fewer bits than the gauge shows."""
    assert not [(a, b) for a in begin for b in begin if a != b and b.startswith(a)], "beginnings must be prefix-free"
    for count in range(MAX_MIDDLES + 1):
        spellings = collections.Counter(
            "".join(middles) + end for middles in itertools.product(MIDDLES, repeat=count) for end in ENDINGS
        )
        clashes = [text for text, seen in spellings.items() if seen > 1]
        assert not clashes, f"{count} middles + ending spell the same text: {clashes[:5]}"


def beginning_page():
    """Every beginning candidate (the 256 most common word starts) with its v5 index or the reason it's out.

    The v5 compiler takes candidates by corpus count, skipping any that clash (one starts the other) with an
    earlier pick, until 128 are chosen. So a skipped token clashes with a more common chosen beginning, and
    a token after the 128th pick is less common than the last one taken.
    """
    model = json.loads(V5_MODEL.read_text())
    text = [v5.text_of(t) for t in model["tokens"]]
    v5.TEXT = text
    counts = v5.count_transitions(v5.corpus_words(), model["tokens"])["begin"]
    index = {token: i for i, token in enumerate(model["begin"])}
    last = min(counts.get(t, 0) for t in model["begin"])
    page = []
    for token in range(v5.NUM_BEGIN):
        entry = {"t": text[token], "id": token, "words": counts.get(token, 0)}
        if token in index:
            entry["i"] = index[token]
        else:
            blockers = [b for b in model["begin"] if v5.conflicts(text[token], text[b])]
            if blockers:
                entry["clash"] = text[max(blockers, key=lambda b: counts.get(b, 0))]
                assert counts.get(token, 0) <= max(counts.get(b, 0) for b in blockers)
            else:
                assert counts.get(token, 0) <= last, text[token]
                entry["less"] = True
        page.append(entry)
    assert sum("i" in e for e in page) == len(model["begin"]) == BEGIN_COUNT
    return [text[t] for t in model["begin"]], page, last


def main():
    model = json.loads(MODEL.read_text())
    tokens = model["tokens"]

    def strip(token):
        return token.strip("^$#")

    def pool(key):
        return {strip(tokens[index]) for row in model[key] for index in row}

    begin, page, last = beginning_page()
    v5_model = json.loads(V5_MODEL.read_text())
    assert all(v5_model["end16"][i] == v5_model["end32"][i][:16] for i in range(len(v5_model["end32"])))
    trigrams = " ".join(sorted(v5.letter_trigrams(v5.corpus_words())))
    assert len(WORDS) == 32 and len(set(WORDS)) == 32 and all(len(w) in (2, 3) for w in WORDS)
    assert len(MIDDLES) == 32 and set(MIDDLES) <= pool("middle32"), set(MIDDLES) - pool("middle32")
    assert len(ENDINGS) == 32 and set(ENDINGS) <= pool("end32"), set(ENDINGS) - pool("end32")
    assert_decodable(begin)
    html = (HERE / "space-game.template.html").read_text()
    for name, values in (("WORDS", WORDS), ("BEGIN", begin), ("CONT", MIDDLES), ("END", ENDINGS),
                         ("BEGIN_PAGE", page), ("BEGIN_LAST", last),
                         ("V5_TOKENS", [v5.text_of(t) for t in v5_model["tokens"]]),
                         ("V5_MIDDLE", v5_model["middle"]), ("V5_END32", v5_model["end32"]),
                         ("TRIGRAMS", trigrams), ("MIN_TRIGRAM_WORDS", v5.MIN_TRIGRAM_WORDS)):
        html = html.replace(f"__{name}__", json.dumps(values, separators=(",", ":")))
    OUT.write_text(html)
    print(f"wrote {OUT}\nbegin: {len(begin)}, middles: {len(MIDDLES)}, endings: {len(ENDINGS)}, short words: {len(WORDS)}")


if __name__ == "__main__":
    main()
