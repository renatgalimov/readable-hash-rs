#!/usr/bin/env python3
"""Phrase tables from more of each language's text: more word forms, weighted by how often they occur.

The per-language word lists (~/data/phrase-langs/words/, made by phrase-corpus/normalize.py) are counts over full
texts: Leipzig sentence corpora (news, web, Wikipedia), subtitles and Tatoeba. The shipped tables use only each
language's 2,500 most frequent words of 4+ letters, each counted once. Here each language keeps up to N forms and
spreads a fixed mass over them:

- uniform: every form counts the same (one more word, one more count, as now);
- log:     a form counts log(1 + its count): the weighting of phonotactic probability (Vitevitch & Luce 2004),
           between counting each form once and counting each occurrence;
- text:    a form counts its number of occurrences: the statistics of running text.

A word found in several languages counts once, with its largest weight (as the shipped list counts it once):
summing would boost words that many languages' news texts share, often English loanwords like "online".
A language's mass is min(its forms, 2,500): the same as now, so a language with 30,000 forms doesn't outweigh one
with 2,500, and the 49 words of Black Speech weigh what they weigh now, not as much as all of English.
The join rule (every 3-letter sequence across a join in 5+ words) still uses the shipped 2,500-word lists: it is a
junk filter, and names, typos and loanwords live in the long tail.

    fulltext.py forms N        # cache each chosen language's top N forms with counts (needs build_corpus.py run first)
    fulltext.py run VARIANT    # compile with that corpus and measure 20,000 phrases; writes results/fulltext-VARIANT.json
"""
import hashlib
import json
import math
import pickle
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HOME = Path.home()
FEATURE = HOME / "projects/readable-hash-rs-phrase/models"
DATA = HOME / "data/phrase-langs"
CACHE = HOME / ".hermes/cache/scratch/fulltext"
OUT = Path(__file__).resolve().parent / "results"
sys.path[:0] = [str(FEATURE), str(FEATURE / "phrase-corpus"), str(Path(__file__).resolve().parent)]
import compile_phrase as c  # noqa: E402

VARIANTS = {"core": (2500, "uniform"), "uniform-30k": (30000, "uniform"), "log-30k": (30000, "log"),
            "text-30k": (30000, "text")}
CORE = 2500


def forms(n):
    """{language: [(form, count)]}: up to n forms of 4+ letters, chosen exactly as build_corpus.py ranks them."""
    import build_corpus as bc
    manifest = json.loads((FEATURE / "training-data/phrase-words.json").read_text())
    out = {}
    for code, info in sorted(manifest["languages"].items()):
        counted, dictionary_only = {}, set()
        min_count = 1 if code in bc.ALWAYS else 2
        for member in info["codes"]:
            for word, count, in_dictionary in bc.read_words(DATA / "words" / f"{member}.tsv.xz"):
                if len(word) < 4:
                    continue
                if count >= min_count:
                    counted[word] = counted.get(word, 0) + count
                elif in_dictionary:
                    dictionary_only.add(word)
        ranked = sorted(counted, key=lambda w: (-counted[w], w))[:n]
        shuffled = sorted(dictionary_only - counted.keys(), key=lambda w: hashlib.sha256(w.encode()).digest())
        out[code] = [(w, counted[w]) for w in ranked] + [(w, 0) for w in shuffled[:n - len(ranked)]]
        print(code, len(out[code]), file=sys.stderr)
    return out


def weights(by_language, scheme):
    total = defaultdict(float)
    for code, rows in by_language.items():
        raw = [1.0 if scheme == "uniform" else math.log1p(max(count, 1)) if scheme == "log" else float(max(count, 1))
               for _, count in rows]
        scale = min(len(rows), CORE) / sum(raw)
        for (word, _), r in zip(rows, raw):
            if re.fullmatch(r"[a-z]+", word):  # a word in several languages counts once, with its largest weight
                total[word] = max(total[word], r * scale)
    return dict(total)


def vocabulary(weight, start_terms, anywhere_terms):
    """compile_phrase.build_vocabulary, with each word counting its weight instead of 1."""
    begin, end, middle = defaultdict(float), defaultdict(float), defaultdict(float)
    for word, w in weight.items():
        n = len(word)
        for length in range(c.MIN_TOKEN, min(c.MAX_TOKEN, n) + 1):
            begin[word[:length]] += w
            end[word[-length:]] += w
        for start in range(1, n - 1):
            for length in range(c.MIN_TOKEN, min(c.MAX_TOKEN, n - 1 - start) + 1):
                middle[word[start:start + length]] += w
    tokens = []
    for counts, size, kind in ((begin, c.NUM_BEGIN, "^"), (end, c.NUM_END, "$"), (middle, c.NUM_MIDDLE, "")):
        top = []
        for text, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
            if c.offensive_token(text, kind == "^", start_terms, anywhere_terms):
                continue
            if kind == "^" and any(c.conflicts(text, other) for other in top):
                continue
            top.append(text)
            if len(top) == size:
                break
        tokens += [("^" + t) if kind == "^" else (t + "$") if kind == "$" else t for t in top]
    return tokens


def transitions(weight, tokens):
    """compile_phrase.count_transitions, weighted."""
    begin_ids = {c.text_of(t): i for i, t in enumerate(tokens[:c.NUM_BEGIN])}
    end_ids = {c.text_of(t): c.NUM_BEGIN + i for i, t in enumerate(tokens[c.NUM_BEGIN:c.NUM_BEGIN + c.NUM_END])}
    middle_ids = {t: c.NUM_BEGIN + c.NUM_END + i for i, t in enumerate(tokens[c.NUM_BEGIN + c.NUM_END:])}
    frequency = {i: 1024 - i % 512 for i in range(1024)}
    begin, middle, ending = Counter(), defaultdict(Counter), defaultdict(Counter)
    segmented = skipped = 0
    for word, w in weight.items():
        ids = c.segment(word, begin_ids, middle_ids, end_ids, frequency) if len(word) >= 2 * c.MIN_TOKEN else None
        if ids is None:
            skipped += 1
            continue
        segmented += 1
        begin[ids[0]] += w
        for previous, following in zip(ids, ids[1:]):
            (ending if c.NUM_BEGIN <= following < c.NUM_BEGIN + c.NUM_END else middle)[previous][following] += w
    return {"begin": begin, "middle": middle, "end": ending, "segmented": segmented, "skipped": skipped}


def run(variant):
    import experiment as ex
    n, scheme = VARIANTS[variant]
    by_language = pickle.loads((CACHE / f"forms-{n}.pkl").read_bytes())
    weight = weights(by_language, scheme)
    c.build_vocabulary = lambda words, start, anywhere: vocabulary(weight, start, anywhere)
    c.count_transitions = lambda words, tokens: transitions(weight, tokens)
    began = time.time()
    model, report = c.compile_model()
    seconds = round(time.time() - began)
    core = c.corpus_words()
    seen3 = c.trigram_counts(core)
    seen4 = Counter(g for w in set(core) for g in {w[i:i + 4] for i in range(len(w) - 3)})
    every_form = {w for rows in pickle.loads((CACHE / "forms-30000.pkl").read_bytes()).values() for w, _ in rows}
    measured = ex.measure(model, every_form, ex.english_words(), ex.load_offensive(), [])
    encode = ex.encoder(model)
    import random
    rng = random.Random(ex.SEED)
    words = [w for _ in range(ex.SAMPLES) for w in encode(rng.getrandbits(64))]
    text = [c.text_of(t) for t in model["tokens"]]
    result = {
        "variant": variant, "forms_per_language": n, "weighting": scheme, "corpus_forms": len(weight),
        "compile_seconds": seconds, "statistics": report["statistics"],
        "chars": measured["chars"], "max_chars": measured["max_chars"],
        "consonant_runs_pct": measured["consonant_runs_pct"], "english_words_pct": measured["english_words_pct"],
        "real_words_any_language_pct": measured["own_words_pct"],
        "offensive_whole_pct": measured["offensive_whole_pct"],
        "rare3_words_pct": round(100 * sum(any(seen3[w[i:i + 3]] < 5 for i in range(len(w) - 2)) for w in words) / len(words), 3),
        "rare4_words_pct": round(100 * sum(any(seen4[w[i:i + 4]] < 5 for i in range(len(w) - 3)) for w in words) / len(words), 3),
        "beginnings": sorted(text[i] for i in model["begin"]),
        "fixed_samples": [" ".join(encode(v)) for v in (0, 42, 0x243f6a8885a308d3, 0xdeadbeefcafebabe, 0x0123456789abcdef,
                                                         0xfedcba9876543210, 2**63, 2**64 - 1)],
        "samples": measured["samples"][:12],
    }
    OUT.mkdir(exist_ok=True)
    (OUT / f"fulltext-{variant}.json").write_text(json.dumps(result, indent=1) + "\n")
    (CACHE / f"model-{variant}.json").write_text(json.dumps(model))
    print(json.dumps({k: v for k, v in result.items() if k not in ("beginnings", "samples", "statistics")}, indent=1))


if __name__ == "__main__":
    CACHE.mkdir(parents=True, exist_ok=True)
    if sys.argv[1] == "forms":
        n = int(sys.argv[2])
        (CACHE / f"forms-{n}.pkl").write_bytes(pickle.dumps(forms(n)))
    else:
        run(sys.argv[2])
