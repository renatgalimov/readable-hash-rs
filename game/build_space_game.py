"""Build the spaces game: a page that walks through encoding one phrase, token by token.

Reads game/space-game.template.html and the phrase tables (models/phrase_model.json) and writes one
self-contained HTML page. The blog embeds it as diagrams/space-game.html.

    python3 game/build_space_game.py [OUT]   # default: game/space-game.html
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "models"))
import compile_phrase as phrase  # noqa: E402

MODEL = HERE.parent / "models/phrase_model.json"


def beginning_page(model, text):
    """Every beginning candidate (the 256 most common word starts) with its index or the reason it's out.

    The compiler takes candidates by corpus count, skipping any that clash (one starts the other) with an
    earlier pick, until 128 are chosen. So a skipped token clashes with a more common chosen beginning, and
    a token after the 128th pick is less common than the last one taken.
    """
    counts = phrase.count_transitions(phrase.corpus_words(), model["tokens"])["begin"]
    index = {token: i for i, token in enumerate(model["begin"])}
    last = min(counts.get(t, 0) for t in model["begin"])
    page = []
    for token in range(phrase.NUM_BEGIN):
        entry = {"t": text[token], "id": token, "words": counts.get(token, 0)}
        if token in index:
            entry["i"] = index[token]
        else:
            blockers = [b for b in model["begin"] if phrase.conflicts(text[token], text[b])]
            if blockers:
                entry["clash"] = text[max(blockers, key=lambda b: counts.get(b, 0))]
                assert counts.get(token, 0) <= max(counts.get(b, 0) for b in blockers)
            else:
                assert counts.get(token, 0) <= last, text[token]
                entry["less"] = True
        page.append(entry)
    assert sum("i" in e for e in page) == len(model["begin"]) == phrase.BEGIN_SIZE
    return page, last


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "space-game.html"
    model = json.loads(MODEL.read_text())
    phrase.validate(model)
    text = [phrase.text_of(t) for t in model["tokens"]]
    phrase.TEXT = text
    assert all(model["end16"][i] == model["end32"][i][:phrase.END_SMALL] for i in range(len(model["end32"])))
    page, last = beginning_page(model, text)
    values = {
        "BEGIN": [text[t] for t in model["begin"]],
        "BEGIN_PAGE": page,
        "BEGIN_LAST": last,
        "V5_TOKENS": text,
        "V5_MIDDLE": model["middle"],
        "V5_END32": model["end32"],
        "TRIGRAMS": " ".join(sorted(phrase.letter_trigrams(phrase.corpus_words()))),
        "MIN_TRIGRAM_WORDS": phrase.MIN_TRIGRAM_WORDS,
    }
    html = (HERE / "space-game.template.html").read_text()
    for name, value in values.items():
        html = html.replace(f"__{name}__", json.dumps(value, separators=(",", ":")))
    assert "__" not in "".join(part for part in html.split("\n") if "const " in part and "= __" in part), "unfilled placeholder"
    out.write_text(html)
    print(f"wrote {out} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
