#!/usr/bin/env python3
"""Compile the phrase tables (format phrase-v5): 11 tokens, 32 layouts, context tables that decode by letters alone.

Format (see src/phrase.rs):
- A phrase is 3 or 4 words, 11 tokens in all; each word is 2-5 tokens: a beginning, 0-3 middles, an ending.
  That gives 32 layouts, so the layout takes the low 5 bits.
- Beginning: 7 bits (128, prefix-free). Middle: 5 bits (32). Ending: 5 bits (32) or 4 bits (16).
  3-word layouts hold 61 token bits and 4-word layouts 63, but only 59 are needed, so the endings of
  words 2 and 3 (3-word layouts) or of every word (4-word layouts) use 16 choices. Every layout is
  then exactly 64 bits.
- Each middle/ending row depends on the previous token (its context).

Table rules:
- No token is shorter than 2 letters. The corpus is re-tokenized with a vocabulary of 2+ letter pieces.
- In every context, the 32 middles and the 32 endings together are prefix-free. So at each point at
  most one token matches the letters, and the decoder finds where a word ends without knowing its
  length. Rows that are prefix-free only separately would be ambiguous (ab+ou+s = ab+ous).
- Every token in a row joins plausibly to its context: each 3-letter sequence across the join occurs in
  some corpus word. This keeps fillers (tokens never seen after the context) from making words like
  bl+ness.
- Every word has a vowel (a, e, i, o, u or y): after a beginning without one, every middle and ending
  has one. Words have at least 2 tokens, so that is enough.
"""
import argparse
import itertools
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "training-data" / "english-lowercase.txt"
MODEL_PATH = ROOT / "phrase_model.json"
REPORT_PATH = ROOT / "phrase_report.json"
RUST_PATH = ROOT.parent / "src" / "phrase_data.rs"

MIN_TOKEN = 2
MAX_TOKEN = 6
NUM_BEGIN, NUM_END, NUM_MIDDLE = 256, 256, 512
BEGIN_SIZE, MIDDLE_SIZE, END_SIZE, END_SMALL = 128, 32, 32, 16
TOTAL_TOKENS, MAX_WORDS, MIN_WORD, MAX_WORD = 11, 4, 2, 5


# ---------------------------------------------------------------- vocabulary and corpus counts

def corpus_words():
    return re.findall(r"[a-z]+", CORPUS.read_text(encoding="utf-8").lower())


def build_vocabulary(words):
    """Top n-grams of 2-6 letters by position: ids 0-255 beginnings, 256-511 endings, 512-1023 middles."""
    begin, end, middle = Counter(), Counter(), Counter()
    for word in words:
        for length in range(MIN_TOKEN, min(MAX_TOKEN, len(word)) + 1):
            begin[word[:length]] += 1
            end[word[-length:]] += 1
        for start in range(1, len(word) - 1):
            for length in range(MIN_TOKEN, MAX_TOKEN + 1):
                if start + length < len(word):
                    middle[word[start:start + length]] += 1
    tokens = []
    for counts, size, kind in ((begin, NUM_BEGIN, "^"), (end, NUM_END, "$"), (middle, NUM_MIDDLE, "")):
        top = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:size]
        assert len(top) == size, (kind, len(top))
        tokens += [("^" + text) if kind == "^" else (text + "$") if kind == "$" else text for text, _ in top]
    return tokens


def text_of(token):
    return token.removeprefix("^").removesuffix("$")


def segment(word, begin_ids, middle_ids, end_ids, frequency):
    """Best split into beginning, middles, ending (all 2+ letters): fewest tokens, then most frequent pieces."""
    n = len(word)
    best = {}  # position -> (tokens, -score, ids) for the best split of word[position:] into middles + ending

    def tail(position):
        if position in best:
            return best[position]
        result = None
        for length in range(MIN_TOKEN, min(MAX_TOKEN, n - position) + 1):
            piece = word[position:position + length]
            if position + length == n:
                if piece in end_ids:
                    option = (1, -math.log(frequency[end_ids[piece]]), (end_ids[piece],))
                    result = option if result is None or option < result else result
            elif piece in middle_ids:
                rest = tail(position + length)
                if rest is not None:
                    token = middle_ids[piece]
                    option = (rest[0] + 1, rest[1] - math.log(frequency[token]), (token,) + rest[2])
                    result = option if result is None or option < result else result
        best[position] = result
        return result

    result = None
    for length in range(MIN_TOKEN, min(MAX_TOKEN, n - MIN_TOKEN) + 1):
        piece = word[:length]
        if piece in begin_ids:
            rest = tail(length)
            if rest is not None:
                token = begin_ids[piece]
                option = (rest[0] + 1, rest[1] - math.log(frequency[token]), (token,) + rest[2])
                result = option if result is None or option < result else result
    return None if result is None else list(result[2])


def count_transitions(words, tokens):
    begin_ids = {text_of(t): i for i, t in enumerate(tokens[:NUM_BEGIN])}
    end_ids = {text_of(t): NUM_BEGIN + i for i, t in enumerate(tokens[NUM_BEGIN:NUM_BEGIN + NUM_END])}
    middle_ids = {t: NUM_BEGIN + NUM_END + i for i, t in enumerate(tokens[NUM_BEGIN + NUM_END:])}
    # Tie-break between equally short splits: prefer pieces ranked higher in their vocabulary block
    # (blocks are sorted by corpus count), using rank as a stand-in for frequency.
    frequency = {i: 1024 - i % 512 for i in range(1024)}
    begin, middle, ending = Counter(), defaultdict(Counter), defaultdict(Counter)
    segmented = skipped = 0
    cache = {}
    for word in words:
        if word not in cache:
            cache[word] = segment(word, begin_ids, middle_ids, end_ids, frequency) if len(word) >= 2 * MIN_TOKEN else None
        ids = cache[word]
        if ids is None:
            skipped += 1
            continue
        segmented += 1
        begin[ids[0]] += 1
        for previous, following in zip(ids, ids[1:]):
            (ending if NUM_BEGIN <= following < NUM_BEGIN + NUM_END else middle)[previous][following] += 1
    return {"begin": begin, "middle": middle, "end": ending, "segmented": segmented, "skipped": skipped}


# ---------------------------------------------------------------- table selection

def context(token):
    return token if token < 256 else token - 256


CONTEXTS = list(range(256)) + list(range(512, 1024))  # beginnings and middles can be followed by a token


def conflicts(a, b):
    return a.startswith(b) or b.startswith(a)


def choose_prefix_free(candidates, size):
    """Greedy: highest (local, global) weight first, skipping any token that is a prefix of a chosen one or vice versa."""
    chosen = []
    for text, _ in sorted(candidates.items(), key=lambda item: (-item[1][0], -item[1][1], item[0])):
        if all(not conflicts(text, other) for other in chosen):
            chosen.append(text)
            if len(chosen) == size:
                return chosen
    raise ValueError("not enough prefix-free tokens")


VOWELS = set("aeiouy")
MIN_TRIGRAM_WORDS = 5  # a 3-letter sequence counts as English if at least this many corpus words contain it


def letter_trigrams(words, minimum=None):
    """3-letter sequences found in at least `minimum` distinct corpus words (one odd word like "bitblt" isn't enough)."""
    minimum = MIN_TRIGRAM_WORDS if minimum is None else minimum
    seen = Counter(trigram for word in set(words) for trigram in {word[i:i + 3] for i in range(len(word) - 2)})
    return {trigram for trigram, count in seen.items() if count >= minimum}


def joins_well(previous_text, token_text, trigrams):
    """Every 3-letter sequence across the join must occur in some corpus word (rules out bl+ness: "bln").

    Tokens are 2+ letters, so the last 2 letters before the join and the first 2 after it cover every
    sequence that crosses it. A token seen after this context in the corpus always passes.
    """
    joined = previous_text[-2:] + token_text[:2]
    return all(joined[i:i + 3] in trigrams for i in range(len(joined) - 2))


def has_vowel(text):
    return bool(VOWELS & set(text))


def choose_row(previous_text, local_middle, local_end, global_middle, global_end, middle_pool, end_pool, trigrams,
               needs_vowel=False):
    """32 middles + 32 endings, prefix-free together, each joining plausibly to the previous token.

    Attested tokens first (by local count, either kind); then filler endings, then filler middles.
    Endings go first among fillers because their pool is half the size. A few tight contexts
    ("qu", "sw": a vowel must follow) have so many attested 2-letter middles that 32 endings can't
    fit; there, the rarest attested middles are treated as fillers, one count level at a time,
    until both rows fill.
    """
    def allowed(token):
        return joins_well(previous_text, TEXT[token], trigrams) and (has_vowel(TEXT[token]) or not needs_vowel)

    middles = [(local_middle.get(t, 0), global_middle[t], "m", t) for t in middle_pool if allowed(t)]
    endings = [(local_end.get(t, 0), global_end[t], "e", t) for t in end_pool if allowed(t)]
    for demoted_below in [0] + sorted({local for local, *_ in middles if local}):
        def order(item):
            local, global_count, kind, token = item
            filler = local == 0 or (kind == "m" and local <= demoted_below)
            return (filler, filler and kind == "m", -local, -global_count, kind, token)

        rows = {"m": [], "e": []}
        limits = {"m": MIDDLE_SIZE, "e": END_SIZE}
        chosen_texts = []
        for _, _, kind, token in sorted(middles + endings, key=order):
            if len(rows[kind]) == limits[kind]:
                continue
            piece = TEXT[token]
            if any(conflicts(piece, other) for other in chosen_texts):
                continue
            rows[kind].append(token)
            chosen_texts.append(piece)
            if len(rows["m"]) == MIDDLE_SIZE and len(rows["e"]) == END_SIZE:
                # The 16-ending row is the first 16 endings in this preference order (a subset stays prefix-free).
                return rows["m"], rows["e"], rows["e"][:END_SMALL]
    raise ValueError(f"row too small after {previous_text!r}")


TEXT = []


def compile_model():
    global TEXT
    words = corpus_words()
    tokens = build_vocabulary(words)
    TEXT = [text_of(t) for t in tokens]
    assert all(len(t) >= MIN_TOKEN for t in TEXT)
    counts = count_transitions(words, tokens)
    trigrams = letter_trigrams(words)
    middle_pool = list(range(512, 1024))
    end_pool = list(range(256, 512))
    global_middle = Counter()
    global_end = Counter()
    for row in counts["middle"].values():
        global_middle.update(row)
    for row in counts["end"].values():
        global_end.update(row)
    middle, end32, end16 = [], [], []
    cache = {}
    for ctx in CONTEXTS:
        local_middle = counts["middle"].get(ctx, Counter())
        local_end = counts["end"].get(ctx, Counter())
        # Every word needs a vowel: words have 2+ tokens, so a beginning without one must be followed by one.
        needs_vowel = ctx < NUM_BEGIN and not has_vowel(TEXT[ctx])
        key = (TEXT[ctx][-2:], needs_vowel, tuple(sorted(local_middle.items())), tuple(sorted(local_end.items())))
        if key not in cache:
            cache[key] = choose_row(TEXT[ctx], local_middle, local_end, global_middle, global_end,
                                    middle_pool, end_pool, trigrams, needs_vowel)
        m, e, e16 = cache[key]
        middle.append(m)
        end32.append(e)
        end16.append(e16)
    begin_candidates = {TEXT[i]: (counts["begin"].get(i, 0), 0) for i in range(NUM_BEGIN)}
    begin_texts = choose_prefix_free(begin_candidates, BEGIN_SIZE)
    begin_index = {TEXT[i]: i for i in range(NUM_BEGIN)}
    begin = [begin_index[t] for t in begin_texts]
    model = {"version": "phrase-v5", "tokens": tokens, "contexts": CONTEXTS, "begin": begin,
             "middle": middle, "end32": end32, "end16": end16}
    validate(model)
    return model, report(model, counts)


def validate(model):
    text = [text_of(t) for t in model["tokens"]]
    trigrams = letter_trigrams(corpus_words())
    assert all(len(t) >= MIN_TOKEN and t.isascii() and t.isalpha() and t.islower() for t in text)
    begin = [text[i] for i in model["begin"]]
    assert len(begin) == BEGIN_SIZE and all(i < 256 for i in model["begin"])
    assert all(not conflicts(a, b) for a, b in itertools.combinations(begin, 2)), "beginnings must be prefix-free"
    for index in range(len(CONTEXTS)):
        m, e, e16 = model["middle"][index], model["end32"][index], model["end16"][index]
        assert len(m) == MIDDLE_SIZE and all(512 <= i < 1024 for i in m)
        assert len(e) == END_SIZE and all(256 <= i < 512 for i in e)
        assert e16 == e[:END_SMALL]
        union = [text[i] for i in m + e]
        assert all(not conflicts(a, b) for a, b in itertools.combinations(union, 2)), f"context {index} not prefix-free"
        previous = text[CONTEXTS[index]]
        assert all(joins_well(previous, piece, trigrams) for piece in union), f"context {index} has an implausible join"
        if CONTEXTS[index] < NUM_BEGIN and not has_vowel(previous):
            assert all(has_vowel(piece) for piece in union), f"beginning {previous!r} allows a word with no vowel"


def report(model, counts):
    """How much of each row was seen after its context in the corpus (higher reads more naturally)."""
    stats = {"corpus_words": counts["segmented"] + counts["skipped"], "segmented_words": counts["segmented"],
             "skipped_words": counts["skipped"]}
    for label, kind in (("middle", "middle"), ("end32", "end"), ("end16", "end")):
        attested = total = 0
        for index, ctx in enumerate(CONTEXTS):
            local = counts[kind].get(ctx, {})
            row = model[label][index]
            attested += sum(1 for t in row if t in local)
            total += len(row)
        stats[f"{label}_attested_fraction"] = attested / total
    stats["begin_attested"] = sum(1 for i in model["begin"] if counts["begin"].get(i))
    return {"statistics": stats}


# ---------------------------------------------------------------- reference codec (mirrors src/phrase.rs)

def layouts():
    result = []
    for words in range(1, MAX_WORDS + 1):
        for lengths in itertools.product(range(MIN_WORD, MAX_WORD + 1), repeat=words):
            if sum(lengths) == TOTAL_TOKENS:
                result.append(lengths)
    result.sort()
    assert len(result) == 32
    return result


def ending_width(word_count, position):
    if word_count == 4:
        return 4
    return 5 if position == 0 else 4


def encode(model, value):
    text = [text_of(t) for t in model["tokens"]]
    lengths = layouts()[value & 31]
    value >>= 5
    words = []
    for position, length in enumerate(lengths):
        token = model["begin"][value & 127]
        value >>= 7
        word = text[token]
        for _ in range(length - 2):
            token = model["middle"][context_index(token)][value & 31]
            value >>= 5
            word += text[token]
        width = ending_width(len(lengths), position)
        row = model["end32"] if width == 5 else model["end16"]
        token = row[context_index(token)][value & ((1 << width) - 1)]
        value >>= width
        words.append(word + text[token])
    assert value == 0
    return " ".join(words)


def context_index(token):
    return context(token)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated files would change")
    args = parser.parse_args()
    model, rep = compile_model()
    outputs = {
        MODEL_PATH: json.dumps(model, sort_keys=True, separators=(",", ":")) + "\n",
        REPORT_PATH: json.dumps(rep, sort_keys=True, indent=1) + "\n",
        RUST_PATH: rust_source(model),
    }
    for path, content in outputs.items():
        if args.check:
            if path.read_text() != content:
                raise SystemExit(f"generated file differs: {path}")
        else:
            path.write_text(content)
    print(json.dumps(rep["statistics"], indent=1))


def rust_source(model):
    out = "// Generated by models/compile_phrase.py; do not edit.\n#![allow(clippy::unreadable_literal)]\n"
    out += "#[rustfmt::skip]\npub static TOKENS: [&str; 1024] = " + json.dumps(model["tokens"]) + ";\n"
    out += f"#[rustfmt::skip]\npub static BEGIN: [u16; {BEGIN_SIZE}] = " + json.dumps(model["begin"]) + ";\n"
    out += f"#[rustfmt::skip]\npub static MIDDLE: [[u16; {MIDDLE_SIZE}]; 768] = " + json.dumps(model["middle"]) + ";\n"
    out += f"#[rustfmt::skip]\npub static END32: [[u16; {END_SIZE}]; 768] = " + json.dumps(model["end32"]) + ";\n"
    out += f"#[rustfmt::skip]\npub static END16: [[u16; {END_SMALL}]; 768] = " + json.dumps(model["end16"]) + ";\n"
    return out


if __name__ == "__main__":
    main()
