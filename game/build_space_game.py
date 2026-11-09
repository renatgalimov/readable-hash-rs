"""Build the spaces game: a page that walks through encoding one phrase, token by token.

Reads game/space-game.template.html and the phrase tables (models/phrase_model.json) and writes one
self-contained HTML page. The blog embeds it as diagrams/space-game.html.

    python3 game/build_space_game.py [OUT]   # default: game/space-game.html
"""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "models"))
import compile_phrase as phrase  # noqa: E402

MODEL = HERE.parent / "models/phrase_model.json"
LANGUAGES = HERE.parent / "models/training-data/phrase-words.json"


def beginning_page(model, text):
    """Every beginning candidate (256 common word starts, none starting another) with its index or why it's out.

    The candidates are already prefix-free and inoffensive (build_vocabulary), so the compiler simply takes the
    128 most common; every other candidate is less common than the last one taken.
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
            assert not any(phrase.conflicts(text[token], text[b]) for b in model["begin"]), text[token]
            assert counts.get(token, 0) <= last, text[token]
            entry["less"] = True
        page.append(entry)
    assert sum("i" in e for e in page) == len(model["begin"]) == phrase.BEGIN_SIZE
    return page, last


def clash_example(model, text, words):
    """A chosen beginning and its most common one-letter-longer word start: the pair no list may hold both of."""
    first = text[model["begin"][0]]
    longer = Counter(w[:len(first) + 1] for w in words if w.startswith(first) and len(w) > len(first) + 2)
    return [first, longer.most_common(1)[0][0]]


def follow_groups(model, previous, kind, size):
    """The token page after `previous` (a token id), as the game sorts it: picked ids and each reason's ids.

    The same rules in the same order as the game page (and the compiler): on the list (picked, or spare when
    only `size` are used), banned after this token, no vowel, letters that don't fit, a clash, less common.
    """
    text = [phrase.text_of(t) for t in model["tokens"]]
    trigrams = phrase.letter_trigrams(phrase.corpus_words())
    row = phrase.context(previous)
    middles, endings = model["middle"][row], model["end32"][row]
    listed = middles if kind == "c" else endings
    banned = set(model["banned"].get(str(previous), []))
    relaxed = previous in model["relaxed"]
    needs_vowel = previous < phrase.NUM_BEGIN and not phrase.has_vowel(text[previous])
    out = {"pick": [], "spare": [], "blocked": [], "vowel": [], "join": [], "clash": [], "less": []}
    for token in range(512, 1024) if kind == "c" else range(256, 512):
        if token in listed:
            out["pick" if listed.index(token) < size else "spare"].append(token)
        elif token in banned:
            out["blocked"].append(token)
        elif needs_vowel and not phrase.has_vowel(text[token]):
            out["vowel"].append(token)
        elif not relaxed and not phrase.joins_well(text[previous], text[token], trigrams):
            out["join"].append(token)
        elif any(phrase.conflicts(text[token], text[u]) for u in middles + endings):
            out["clash"].append(token)
        else:
            out["less"].append(token)
    return out


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
        "BEGIN_EXAMPLE": clash_example(model, text, phrase.corpus_words()),
        "TABLE_TOKENS": text,
        "TABLE_MIDDLE": model["middle"],
        "TABLE_END32": model["end32"],
        "TABLE_BANNED": model["banned"],
        "TABLE_RELAXED": model["relaxed"],
        "LANGUAGES": len(json.loads(LANGUAGES.read_text())["languages"]),
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
