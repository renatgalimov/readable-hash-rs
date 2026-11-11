"""Build the spaces game: a page that walks through encoding one phrase, token by token.

Reads game/space-game.template.html and the phrase tables (models/phrase_model.json) and writes the page,
plus <name>-origins.js next to it: which languages each token comes from (about 600 KB, so the page loads it
with a deferred script and works without it). The blog embeds them as diagrams/space-game.html.

    python3 game/build_space_game.py [OUT]   # default: game/space-game.html (+ game/space-game-origins.js)
"""
import argparse
import json
import lzma
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "models"))
import compile_phrase as phrase  # noqa: E402

MODEL = HERE.parent / "models/phrase_model.json"
LANGUAGES = HERE.parent / "models/training-data/phrase-words.json"
LANGUAGE_WORDS = HERE.parent / "models/training-data/phrase-languages.txt.xz"
# How each language writes the words (onlarin -> onların), and a table folding each letter of those spellings.
ORIGINALS = HERE.parent / "models/training-data/phrase-originals.txt.xz"
WIKIPEDIA = HERE.parent / "models/phrase-corpus/language-wikipedia.json"  # code -> English Wikipedia article


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


def follow_groups(model, previous, kind):
    """The token page after `previous` (a token id), as the game sorts it: picked ids and each reason's ids.

    The same rules in the same order as the game page (and the compiler): on the list, banned after this token, no vowel, a letter or three vowels in a row, letters that don't
    fit (at this context's minimum), a clash, less common.
    """
    text = [phrase.text_of(t) for t in model["tokens"]]
    minimum = model["relaxed"].get(str(previous), phrase.MIN_TRIGRAM_WORDS)
    trigrams = phrase.letter_trigrams(phrase.corpus_words(), minimum)
    row = phrase.context(previous)
    middles, endings = model["middle"][row], model["end32"][row]
    listed = middles if kind == "c" else endings
    banned = set(model["banned"].get(str(previous), []))
    needs_vowel = previous < phrase.NUM_BEGIN and not phrase.has_vowel(text[previous])
    out = {"pick": [], "blocked": [], "vowel": [], "triple": [], "join": [], "clash": [], "less": []}
    for token in range(512, 1024) if kind == "c" else range(256, 512):
        if token in listed:
            out["pick"].append(token)
        elif token in banned:
            out["blocked"].append(token)
        elif needs_vowel and not phrase.has_vowel(text[token]):
            out["vowel"].append(token)
        elif not phrase.triple_free(text[previous], text[token]):
            out["triple"].append(token)
        elif not phrase.joins_well(text[previous], text[token], trigrams):
            out["join"].append(token)
        elif any(phrase.conflicts(text[token], text[u]) for u in middles + endings):
            out["clash"].append(token)
        else:
            out["less"].append(token)
    return out



def b36(n):
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while True:
        n, r = divmod(n, 36)
        out = digits[r] + out
        if not n:
            return out


class Origins:
    """Which languages' words each token comes from, packed for the page.

    Every word of every language is split into tokens the way the compiler splits the word list. A beginning
    comes from the words it starts; a middle or ending on a list comes from the words where it follows that
    list's previous token; a filler (on a list, but never after that token) is described by where the token is
    common overall. Languages are ordered by how many of their words have it, then by corpus size.

    The example word is the one shared by most languages among the top languages' own most common examples;
    every language whose list has it is named with it (largest corpus first, up to SAME, then a count), and up to
    ALSO other top languages follow. The word is shown as each named language writes it (onların in Turkish, not
    the folded onlarin): one group per spelling. Packed entry: "n|word:lang,lang|word:lang;more|:lang,lang" (base 36;
    n = number of languages, words index EXAMPLES, more = how many further languages have the word, after the last
    spelling), "" when there is none. One word per entry keeps the file at about 600 KB instead of 850 KB.
    """

    CANDIDATES, SAME, ALSO = 5, 3, 2

    def __init__(self, model, text):
        info = json.loads(LANGUAGES.read_text())["languages"]
        lists = lzma.decompress(LANGUAGE_WORDS.read_bytes()).decode().splitlines()
        by_language = {code: words.split() for code, words in (line.split("\t") for line in lists)}
        self.codes = sorted(by_language, key=lambda code: -info[code]["words"])  # index 0 = largest corpus
        # Display names: drop qualifiers ("Dimli (individual language)"); name the two group codes and Estonian plainly.
        plain = {"ber": "Berber", "roa": "Romance", "et": "Estonian"}
        self.names = [plain.get(code) or re.sub(r"\s*\(.*\)", "", info[code]["name"]) for code in self.codes]
        wikipedia = json.loads(WIKIPEDIA.read_text())
        self.links = [wikipedia[code] for code in self.codes]
        language = {code: i for i, code in enumerate(self.codes)}
        self.fold, self.original = {}, {}  # letter -> its ASCII letters; language index -> {folded word: original}
        for line in lzma.decompress(ORIGINALS.read_bytes()).decode().splitlines():
            code, pairs = line.split("\t")
            entries = dict(pair.split("=", 1) for pair in pairs.split())
            if code == "*":
                self.fold = entries
            elif code in language:
                self.original[language[code]] = entries
        begin_ids = {text[i]: i for i in range(phrase.NUM_BEGIN)}
        end_ids = {text[i]: i for i in range(phrase.NUM_BEGIN, phrase.NUM_BEGIN + phrase.NUM_END)}
        middle_ids = {text[i]: i for i in range(phrase.NUM_BEGIN + phrase.NUM_END, 1024)}
        frequency = {i: 1024 - i % 512 for i in range(1024)}  # the compiler's tie-break
        split = {}
        self.has = defaultdict(set)  # word -> indices of the languages whose lists have it
        self.seen = defaultdict(dict)  # key -> language index -> [words, example, rank]
        for code, words in by_language.items():
            for rank, word in enumerate(words):
                self.has[word].add(language[code])
                if word not in split:
                    split[word] = (phrase.segment(word, begin_ids, middle_ids, end_ids, frequency)
                                   if len(word) >= 2 * phrase.MIN_TOKEN else None)
                ids = split[word]
                if not ids:
                    continue
                keys = {("begin", ids[0])} | set(zip(ids, ids[1:])) | {("token", t) for t in ids[1:]}
                for key in keys:
                    entry = self.seen[key].setdefault(language[code], [0, word, rank])
                    entry[0] += 1
                    if rank < entry[2]:
                        entry[1], entry[2] = word, rank
        self.words, self.folds, self.word_index = [], [], {}  # shown spellings, their folded words, spelling -> index

    def pack(self, key):
        found = self.seen.get(key)
        if not found:
            return ""
        ranked = [lang for lang, _ in sorted(found.items(), key=lambda item: (-item[1][0], item[0], item[1][2]))]
        order = {lang: i for i, lang in enumerate(ranked)}
        candidates = [found[lang][1] for lang in ranked[:self.CANDIDATES]]
        word = max(candidates, key=lambda w: (len(self.has[w] & found.keys()), -candidates.index(w)))
        same = sorted(self.has[word] & found.keys())  # by corpus size: the best-known languages first
        also = [lang for lang in ranked if lang not in self.has[word]][:self.ALSO]
        spellings = {}  # how the named languages write the word -> those languages, in the order they're named
        for lang in same[:self.SAME]:
            spellings.setdefault(self.original.get(lang, {}).get(word, word), []).append(lang)
        parts = [b36(len(found))]
        for i, (shown, langs) in enumerate(spellings.items()):
            if shown not in self.word_index:
                self.word_index[shown] = len(self.words)
                self.words.append(shown)
                self.folds.append(word)
            part = b36(self.word_index[shown]) + ":" + ",".join(b36(lang) for lang in langs)
            if i == len(spellings) - 1 and len(same) > self.SAME:
                part += ";" + b36(len(same) - self.SAME)
            parts.append(part)
        if also:
            parts.append(":" + ",".join(b36(lang) for lang in also))
        return "|".join(parts)


def ban_reasons(model, text):
    """For each banned token on a page: the offensive term it would spell and the lists that have the term.

    A direct ban spells the term with the previous token. A ban found by the compiler's walk spells it across
    more tokens; the walk is repeated on the final tables to find the word. If no path still leads there (the
    ban was found in an earlier draft of the tables), the term is unknown (-1). Returns (terms, list language
    names, their Wikipedia articles, {context: packed term indices aligned with model["banned"][context]},
    dropped beginnings).
    """
    start_terms, anywhere_terms = phrase.blocklist()
    starts, anywhere = set(start_terms), set(anywhere_terms)
    sources = {}
    for line in phrase.read_text(phrase.BLOCKLIST).splitlines():
        term, names = line.split("\t")
        sources[term] = sorted({name.split("-")[1] for name in names.split(",")})
    list_names = json.loads(LANGUAGES.read_text())["list_languages"]
    list_codes = sorted(list_names, key=lambda code: (code != "en", list_names[code]))
    list_index = {code: i for i, code in enumerate(list_codes)}
    terms, term_index = [], {}

    def term_in(spelled, last):
        """The longest term that ends inside the last `last` letters of "^" + the word's letters."""
        best = None
        for end in range(len(spelled) - last + 1, len(spelled) + 1):
            for begin in range(0, end - 2):
                piece = spelled[begin:end]
                term = piece[1:] if piece.startswith("^") and piece[1:] in starts else piece if piece in anywhere else None
                if term and (best is None or len(term) > len(best)):
                    best = term
        if best is None:
            return -1
        if best not in term_index:
            term_index[best] = len(terms)
            terms.append([best, [list_index[code] for code in sorted(sources[best], key=lambda c: list_index[c])]])
        return term_index[best]

    known = {}
    for ctx, tokens in model["banned"].items():
        ctx = int(ctx)
        prefix = "^" + text[ctx] if ctx < phrase.NUM_BEGIN else text[ctx]
        for token in tokens:
            found = term_in(prefix + text[token], len(text[token]))
            if found >= 0:
                known[(ctx, token)] = found
    # Bans that span more tokens: walk the final tables from every beginning.
    machine = phrase.Terms(start_terms, anywhere_terms)
    wanted = defaultdict(set)
    for ctx, tokens in model["banned"].items():
        for token in tokens:
            if (int(ctx), token) not in known:
                wanted[int(ctx)].add(token)
    stack = [(b, machine.feed(0, "^" + text[b])[0], 0, "^" + text[b]) for b in model["begin"]]
    seen = set()
    while stack:
        token, state, middles, spelled = stack.pop()
        if (token, state, middles) in seen:
            continue
        seen.add((token, state, middles))
        for following in list(wanted.get(token, ())):
            if machine.feed(state, text[following])[1]:
                known[(token, following)] = term_in(spelled + text[following], len(text[following]))
                wanted[token].discard(following)
            elif following >= phrase.NUM_BEGIN + phrase.NUM_END:
                # A ban at the join before a middle (bi+ch, when bi+ch+a... spells "bicha"): the term completes in
                # a token of the middle's own row.
                after = machine.feed(state, text[following])[0]
                row = phrase.context(following)
                for next_token in model["middle"][row] + model["end32"][row]:
                    if machine.feed(after, text[next_token])[1]:
                        known[(token, following)] = term_in(spelled + text[following] + text[next_token],
                                                            len(text[following]) + len(text[next_token]))
                        wanted[token].discard(following)
                        break
        if middles < phrase.MAX_WORD - 2:
            for middle in model["middle"][phrase.context(token)]:
                state_after, hit = machine.feed(state, text[middle])
                if not hit:
                    stack.append((middle, state_after, middles + 1, spelled + text[middle]))
    packed = {ctx: " ".join(b36(known.get((int(ctx), t), -1) + 1) for t in tokens) for ctx, tokens in model["banned"].items()}
    # Word starts the compiler dropped before choosing the 256 candidates, because they are offensive themselves.
    begin = Counter()
    for word in phrase.corpus_words():
        for length in range(phrase.MIN_TOKEN, min(phrase.MAX_TOKEN, len(word)) + 1):
            begin[word[:length]] += 1
    taken, dropped = [], []
    for piece, count in sorted(begin.items(), key=lambda item: (-item[1], item[0])):
        if phrase.offensive_token(piece, True, start_terms, anywhere_terms):
            dropped.append([piece, count, term_in("^" + piece, len(piece))])
            continue
        if not any(phrase.conflicts(piece, other) for other in taken):
            taken.append(piece)
            if len(taken) == phrase.NUM_BEGIN:
                break
    assert taken == [text[i] for i in range(phrase.NUM_BEGIN)], "candidate order differs from the compiler's"
    wikipedia = json.loads(WIKIPEDIA.read_text())
    return terms, [list_names[code] for code in list_codes], [wikipedia[code] for code in list_codes], packed, dropped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out", nargs="?", type=Path)
    args = parser.parse_args()
    out = args.out or HERE / "space-game.html"
    model = json.loads(MODEL.read_text())
    phrase.validate(model)
    text = [phrase.text_of(t) for t in model["tokens"]]
    phrase.TEXT = text
    page, last = beginning_page(model, text)
    origins = Origins(model, text)
    begin_origin = {t: origins.pack(("begin", t)) for t in model["begin"]}
    follow_origin = {}
    for ctx in model["begin"] + list(range(phrase.NUM_BEGIN + phrase.NUM_END, 1024)):
        row = phrase.context(ctx)
        follow_origin[ctx] = " ".join(origins.pack((ctx, t)) for t in model["middle"][row] + model["end32"][row])
    token_origin = {t: origins.pack(("token", t)) for t in range(phrase.NUM_BEGIN, 1024)}
    for ctx, packed in follow_origin.items():  # sanity: every example word has the previous token, then this one
        row = phrase.context(ctx)
        for t, entry in zip(model["middle"][row] + model["end32"][row], packed.split(" ")):
            for group in entry.split("|")[1:2]:
                word = origins.folds[int(group.split(":")[0], 36)]
                pair = text[ctx] + text[t]
                assert (word.endswith(pair) if t < phrase.NUM_BEGIN + phrase.NUM_END else pair in word[:-2]) and \
                    (ctx >= phrase.NUM_BEGIN or word.startswith(text[ctx])), (text[ctx], text[t], word)
    terms, list_names, list_links, ban_terms, dropped = ban_reasons(model, text)
    values = {
        # The phrase format: tokens per phrase, most words, word lengths.
        "FORMAT": {"TOTAL_TOKENS": phrase.TOTAL_TOKENS, "MAX_WORDS": phrase.MAX_WORDS,
                   "LENGTHS": list(range(phrase.MIN_WORD, phrase.MAX_WORD + 1))},
        "BEGIN": [text[t] for t in model["begin"]],
        "BEGIN_PAGE": page,
        "BEGIN_LAST": last,
        "BEGIN_EXAMPLE": clash_example(model, text, phrase.corpus_words()),
        "TABLE_TOKENS": text,
        "TABLE_MIDDLE": model["middle"],
        "TABLE_END32": model["end32"],
        "TABLE_BANNED": model["banned"],
        "TABLE_RELAXED": model["relaxed"],
        "ORIGINS_FILE": out.with_name(out.stem + "-origins.js").name,
        "BAN_TERMS": ban_terms,
        "TERMS": terms,
        "LIST_NAMES": list_names,
        "LIST_LINKS": list_links,
        "BANNED_BEGIN": dropped,
        "LANGUAGES": len(json.loads(LANGUAGES.read_text())["languages"]),
        "TRIGRAMS": " ".join(sorted(phrase.letter_trigrams(phrase.corpus_words()))),
        # Sequences in 1-4 words, for the contexts whose join minimum is lower (model["relaxed"]).
        "RARE_TRIGRAMS": " ".join(f"{t}:{n}" for t, n in sorted(phrase.trigram_counts(phrase.corpus_words()).items())
                                  if n < phrase.MIN_TRIGRAM_WORDS),
        "MIN_TRIGRAM_WORDS": phrase.MIN_TRIGRAM_WORDS,
    }
    html = (HERE / "space-game.template.html").read_text()
    for name, value in values.items():
        html = html.replace(f"__{name}__", json.dumps(value, separators=(",", ":")))
    assert "__" not in "".join(part for part in html.split("\n") if "const " in part and "= __" in part), "unfilled placeholder"
    out.write_text(html)
    for shown, folded in zip(origins.words, origins.folds):  # the page folds letter by letter to find the token
        assert "".join(origins.fold.get(ch, ch) for ch in shown) == folded, (shown, folded)
    used = {ch for shown in origins.words for ch in shown}
    data = {"LANG_NAMES": origins.names, "LANG_LINKS": origins.links, "EXAMPLES": " ".join(origins.words),
            "FOLD": {ch: ascii for ch, ascii in origins.fold.items() if ch in used}, "BEGIN": begin_origin,
            "FOLLOW": follow_origin, "TOKEN": token_origin}
    script = ("// Generated by game/build_space_game.py: where each token of the phrase tables comes from.\n"
              f"window.SPACE_GAME_ORIGINS = {json.dumps(data, separators=(',', ':'))};\n"
              "if (window.onSpaceGameOrigins) window.onSpaceGameOrigins();\n")
    origins_out = out.with_name(out.stem + "-origins.js")
    origins_out.write_text(script)
    print(f"wrote {out} ({len(html) // 1024} KB) and {origins_out.name} ({len(script) // 1024} KB)")


if __name__ == "__main__":
    main()
