#!/usr/bin/env python3
"""Build phrase-v5 tables from any word list and measure them: length, pronounceability, real words, offensiveness.

The tables use the frozen v5 compiler (readable-hash-rs-phrase/models/compile_phrase.py) and its rules unchanged,
with one experiment-only relaxation: when a row can't be filled under the join rule (some languages allow very few
letters after certain consonant pairs), that row is filled without the join rule and counted in `relaxed_rows`.
Rows stay prefix-free, so every phrase still decodes.

    .venv/bin/python experiment.py zu tr fi ...      # one result per language in results/<code>.json
    .venv/bin/python experiment.py --mix zu+tr ...   # a mix: the languages' word lists combined
"""
import argparse
import collections
import inspect
import json
import lzma
import random
import re
import statistics
import sys
import tempfile
import time
from pathlib import Path

from anyascii import anyascii

HERE = Path(__file__).resolve().parent
DATA = Path.home() / "data" / "phrase-langs"
WORDS, RAW = DATA / "words", DATA / "raw"
RESULTS = HERE / "results"
sys.path.insert(0, str(Path.home() / "projects/readable-hash-rs-phrase/models"))
import compile_phrase as compiler  # noqa: E402

SAMPLES = 20_000
SEED = 20261108
MAX_WORDS = 80_000
VOWELS = set("aeiouy")


# ----------------------------------------------------------------------------------------------- word lists
def load_words(code, limit=MAX_WORDS, exclude=frozenset()):
    """The language's most frequent words (count >= 2), topped up with dictionary words if text is scarce."""
    text, dictionary = [], []
    with lzma.open(WORDS / f"{code}.tsv.xz", "rt", encoding="utf-8") as lines:
        for line in lines:
            word, count, in_dictionary = line.rstrip("\n").split("\t")
            if word in exclude:
                continue
            if int(count) >= 2:
                text.append(word)
            elif in_dictionary == "1":
                dictionary.append(word)
    return (text + dictionary)[:limit]


def english_words():
    return set(Path.home().joinpath("projects/readable-hash-rs-phrase/models/training-data/english-lowercase.txt")
               .read_text().split())


# ----------------------------------------------------------------------------------------------- offensive words
def fold(term):
    return re.sub(r"[^a-z ]", "", anyascii(term).lower()).strip()


def load_offensive():
    """{folded term: set of list languages}. Single words and multi-word phrases (matched across words)."""
    terms = collections.defaultdict(set)
    for path in (RAW / "profanity").glob("ldnoobw_*.txt"):
        lang = path.stem.split("_", 1)[1].split("-")[0]
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if (term := fold(line)) and len(term.replace(" ", "")) >= 3:
                terms[term].add(lang)
    soap = RAW / "profanity" / "washyourmouthoutwithsoap.json"
    if soap.exists():
        for lang, words in json.loads(soap.read_text()).items():
            for word in words:
                if (term := fold(word)) and len(term.replace(" ", "")) >= 3:
                    terms[term].add(lang)
    dsojevic = RAW / "profanity" / "dsojevic_en.json"
    if dsojevic.exists():
        for entry in json.loads(dsojevic.read_text()):
            for match in entry.get("match", "").split("|"):
                if (term := fold(match.replace("*", ""))) and len(term.replace(" ", "")) >= 3:
                    terms[term].add("en")
    return terms


# ----------------------------------------------------------------------------------------------- tables
class Everything:
    def __contains__(self, _):
        return True


def blocking_compile_model(banned_terms, extra_pairs=frozenset()):
    """compile_model with one change: a row's candidates exclude tokens that would spell a banned term.

    Rows are cached per context (not per last two letters), because a ban depends on the whole previous token.
    A token is banned after context `ctx` if ctx + token contains a banned term of 5+ letters, or, right after a
    beginning, if the word would start with a banned 4-letter term the beginning doesn't already start with.
    3-letter terms aren't banned: words have 4+ letters, and banning them inside words removes too much.
    If a row can't be filled with the bans, it is filled without them (counted in `unbanned_rows`).
    """
    long_terms = sorted(t for t in banned_terms if len(t) >= 5)
    short_terms = tuple(t for t in banned_terms if len(t) == 4)
    long_pattern = re.compile("|".join(map(re.escape, long_terms))) if long_terms else None
    source = inspect.getsource(compiler.compile_model)
    source = source.replace("key = (TEXT[ctx][-2:],", "key = (ctx, TEXT[ctx][-2:],")
    # the original choose_row reads the compiler module's TEXT: keep it in sync with this copy's
    source = source.replace("TEXT = [text_of(t) for t in tokens]", "TEXT = [text_of(t) for t in tokens]\n    SYNC_TEXT(TEXT)")
    source = source.replace("cache[key] = choose_row(TEXT[ctx],", "cache[key] = BANNED_ROW(ctx, TEXT[ctx],")
    assert "key = (ctx," in source and "SYNC_TEXT(TEXT)" in source and "BANNED_ROW(ctx" in source
    stats = collections.Counter()
    namespace = dict(compiler.__dict__)

    def ban(ctx, token):
        if (ctx, token) in extra_pairs:
            return True
        text = namespace["TEXT"]
        joined = text[ctx] + text[token]
        if long_pattern is not None and long_pattern.search(joined):
            return True
        return ctx < compiler.NUM_BEGIN and joined.startswith(short_terms) and not text[ctx].startswith(short_terms)

    def banned_row(ctx, previous_text, local_middle, local_end, global_middle, global_end, middle_pool, end_pool,
                   trigrams, needs_vowel):
        middles = [t for t in middle_pool if not ban(ctx, t)]
        endings = [t for t in end_pool if not ban(ctx, t)]
        stats["banned_pairs"] += len(middle_pool) - len(middles) + len(end_pool) - len(endings)
        choose = namespace["choose_row"]
        try:
            return choose(previous_text, local_middle, local_end, global_middle, global_end, middles, endings, trigrams, needs_vowel)
        except ValueError:
            stats["unbanned_rows"] += 1
            return choose(previous_text, local_middle, local_end, global_middle, global_end, middle_pool, end_pool,
                          trigrams, needs_vowel)

    namespace["BANNED_ROW"] = banned_row
    namespace["SYNC_TEXT"] = lambda text: setattr(compiler, "TEXT", text)
    exec(compile(source, compiler.__file__, "exec"), namespace)  # noqa: S102  (experiment-only variant)
    return namespace, stats


def three_token_spans(model, banned_terms):
    """(middle, next token) pairs where (end of the previous token) + middle + (start of next) spells a banned term.

    Only matches that touch all three tokens count; two-token matches are already banned row by row.
    """
    long_terms = sorted(t for t in banned_terms if len(t) >= 5)
    if not long_terms:
        return set()
    pattern = re.compile("(?=(" + "|".join(map(re.escape, long_terms)) + "))")
    text = [compiler.text_of(t) for t in model["tokens"]]
    rows = {ctx: model["middle"][compiler.context(ctx)] + model["end32"][compiler.context(ctx)] for ctx in model["contexts"]}
    # which middles can follow which tokens, starting from the beginnings actually in use
    predecessors = collections.defaultdict(set)
    frontier, seen = list(model["begin"]), set(model["begin"])
    while frontier:
        ctx = frontier.pop()
        for middle in model["middle"][compiler.context(ctx)]:
            predecessors[middle].add(text[ctx][-4:])
            if middle not in seen:
                seen.add(middle)
                frontier.append(middle)
    found = set()
    for middle, suffixes in predecessors.items():
        for suffix in suffixes:
            for following in rows[middle]:
                joined = suffix + text[middle] + text[following]
                start_of_middle, end_of_middle = len(suffix), len(suffix) + len(text[middle])
                for match in pattern.finditer(joined):
                    term = match.group(1)
                    if match.start() < start_of_middle and match.start() + len(term) > end_of_middle:
                        found.add((middle, following))
    return found


ORIGINAL_BUILD_VOCABULARY = compiler.build_vocabulary


def prefix_free_vocabulary(words):
    """build_vocabulary, but the 256 beginning candidates are a prefix-free set chosen from all word starts.

    Experiment-only fallback for languages whose 256 most common word starts are long chains (co, con, cont...)
    with fewer than 128 prefix-free members, so the compiler can't pick its 128 beginnings.
    """
    tokens = ORIGINAL_BUILD_VOCABULARY(words)
    starts = collections.Counter()
    for word in words:
        for length in range(compiler.MIN_TOKEN, min(compiler.MAX_TOKEN, len(word)) + 1):
            starts[word[:length]] += 1
    ranked = [text for text, _ in sorted(starts.items(), key=lambda item: (-item[1], item[0]))]
    chosen = []
    for text in ranked:
        if all(not compiler.conflicts(text, other) for other in chosen):
            chosen.append(text)
            if len(chosen) == compiler.NUM_BEGIN:
                break
    taken = set(chosen)
    for text in ranked:
        if len(chosen) == compiler.NUM_BEGIN:
            break
        if text not in taken:
            chosen.append(text)
            taken.add(text)
    return ["^" + text for text in chosen] + tokens[compiler.NUM_BEGIN:]


def build_tables(words, banned_terms=None, extra_pairs=frozenset()):
    """Compile v5 tables from `words` (a list). Returns (model, info)."""
    try:
        return compile_tables(words, banned_terms, extra_pairs)
    except ValueError as error:
        if "prefix-free" not in str(error):
            raise
    compiler.build_vocabulary = prefix_free_vocabulary
    try:
        model, info = compile_tables(words, banned_terms, extra_pairs)
    finally:
        compiler.build_vocabulary = ORIGINAL_BUILD_VOCABULARY
    return model, {**info, "beginning_fallback": True}


def compile_tables(words, banned_terms=None, extra_pairs=frozenset()):
    relaxed = []
    original_choose, original_validate = compiler.choose_row, compiler.validate

    def choose_row(previous_text, *rest):
        try:
            return original_choose(previous_text, *rest)
        except ValueError:
            rest = list(rest)
            rest[6] = Everything()  # the trigram set: accept every join for this row only
            relaxed.append(previous_text)
            return original_choose(previous_text, *rest)

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as corpus:
        corpus.write("\n".join(words) + "\n")
    compiler.CORPUS = Path(corpus.name)
    compiler.choose_row, compiler.validate = choose_row, lambda model: None
    banned_count = collections.Counter()
    try:
        if banned_terms:
            namespace, banned_count = blocking_compile_model(banned_terms, extra_pairs)
            # the exec'd copy looks names up in its own namespace: route choose_row/validate/CORPUS through it
            namespace.update(choose_row=choose_row, validate=lambda model: None, CORPUS=compiler.CORPUS)
            model, report = namespace["compile_model"]()
        else:
            model, report = compiler.compile_model()
    finally:
        compiler.choose_row, compiler.validate = original_choose, original_validate
        Path(corpus.name).unlink()
    text = [compiler.text_of(t) for t in model["tokens"]]
    for row in range(len(model["middle"])):  # the codec's own invariant: middles + endings prefix-free per row
        union = [text[t] for t in model["middle"][row] + model["end32"][row]]
        assert all(not compiler.conflicts(a, b) for i, a in enumerate(union) for b in union[i + 1:]), row
    return model, {"relaxed_rows": len(relaxed), "relaxed_examples": relaxed[:12],
                   **dict(banned_count), **report.get("statistics", report)}


def encoder(model):
    text = [compiler.text_of(t) for t in model["tokens"]]
    layouts = compiler.layouts()

    def encode(value):
        lengths = layouts[value & 31]
        value >>= 5
        words = []
        for position, length in enumerate(lengths):
            token = model["begin"][value & 127]
            value >>= 7
            word = text[token]
            for _ in range(length - 2):
                token = model["middle"][compiler.context(token)][value & 31]
                value >>= 5
                word += text[token]
            width = compiler.ending_width(len(lengths), position)
            row = model["end32"] if width == 5 else model["end16"]
            token = row[compiler.context(token)][value & ((1 << width) - 1)]
            value >>= width
            words.append(word + text[token])
        return words

    return encode


# ----------------------------------------------------------------------------------------------- measuring
def load_severe():
    """English terms rated severity 3+ (of 4) or tagged racial/religious/lgbtq in the dsojevic list."""
    path = RAW / "profanity" / "dsojevic_en.json"
    severe = set()
    for entry in json.loads(path.read_text()) if path.exists() else []:
        if entry.get("severity", 0) >= 3 or {"racial", "religious", "lgbtq"} & set(entry.get("tags", [])):
            severe |= {fold(m.replace("*", "")) for m in entry.get("match", "").split("|")}
    return {t for t in severe if len(t) >= 3}


SEVERE = None
MAJOR = {"en", "es", "fr", "de", "pt", "ru", "it", "tr", "zh", "ja", "ar", "hi", "id"}  # most-spoken languages


def measure(model, own_words, english, offensive, own_codes=()):
    global SEVERE
    SEVERE = SEVERE if SEVERE is not None else load_severe()
    encode = encoder(model)
    rng = random.Random(SEED)
    phrases = [encode(rng.getrandbits(64)) for _ in range(SAMPLES)]
    words = [w for p in phrases for w in p]
    single = {t: langs for t, langs in offensive.items() if " " not in t}
    multi = {t: langs for t, langs in offensive.items() if " " in t}
    long5 = [t for t in single if len(t) >= 5]
    long4 = [t for t in single if len(t) == 4]
    hits = collections.Counter()
    whole = inside5 = inside4 = across = 0
    english_whole = severe = own_whole = major_whole = 0
    own_codes = set(own_codes)
    examples = collections.defaultdict(list)
    for phrase in phrases:
        joined = " ".join(phrase)
        found_whole = [w for w in phrase if w in single]
        found5 = [(t, w) for w in phrase if w not in single for t in long5 if t in w]
        found4 = [(t, w) for w in phrase if w not in single for t in long4 if t in w]
        found_multi = [t for t in multi if t in joined]
        whole += bool(found_whole)
        english_whole += any("en" in single[w] for w in found_whole)
        own_whole += any(single[w] & own_codes for w in found_whole)
        major_whole += any(single[w] & MAJOR for w in found_whole)
        severe += any(w in SEVERE for w in phrase) or any(t in w for w in phrase for t in SEVERE if len(t) >= 5)
        inside5 += bool(found5)
        inside4 += bool(found4 or found5)
        across += bool(found_multi)
        for w in found_whole:
            hits[w] += 1
            if len(examples[w]) < 2:
                examples[w].append(joined)
        for t, w in found5:
            hits[t] += 1
            if len(examples[t]) < 2:
                examples[t].append(joined)
    pct = lambda n, d=len(phrases): round(100 * n / d, 3)  # noqa: E731
    return {
        "chars": round(statistics.mean(len(" ".join(p)) for p in phrases), 2),
        "max_chars": max(len(" ".join(p)) for p in phrases),
        "consonant_runs_pct": pct(sum(bool(re.search(r"[^aeiouy]{3,}", w)) for w in words), len(words)),
        "vowel_runs_pct": pct(sum(bool(re.search(r"[aeiouy]{3,}", w)) for w in words), len(words)),
        "english_words_pct": pct(sum(w in english for w in words), len(words)),
        "own_words_pct": pct(sum(w in own_words for w in words), len(words)),
        "offensive_whole_pct": pct(whole),
        "offensive_whole_english_list_pct": pct(english_whole),
        "offensive_whole_own_list_pct": pct(own_whole),
        "offensive_whole_major_lists_pct": pct(major_whole),
        "offensive_severe_en_pct": pct(severe),
        "offensive_inside5_pct": pct(inside5),
        "offensive_inside4_pct": pct(inside4),
        "offensive_across_words_pct": pct(across),
        "top_hits": [(t, n, sorted(offensive[t]), examples[t]) for t, n in hits.most_common(15)],
        "samples": [" ".join(p) for p in phrases[:12]],
    }


def run(name, words, english, offensive, extra=None, banned_terms=None):
    start = time.time()
    model, info = build_tables(words, banned_terms)
    if banned_terms:
        # ban three-token spellings too: find them in the built tables, ban the last pair, rebuild; repeat
        extra_pairs, rounds = set(), []
        for _ in range(4):
            spans = three_token_spans(model, banned_terms) - extra_pairs
            rounds.append(len(spans))
            if not spans:
                break
            extra_pairs |= spans
            model, info = build_tables(words, banned_terms, frozenset(extra_pairs))
        info["three_token_rounds"] = rounds
    codes = (extra or {}).get("languages", [])
    result = {"name": name, "corpus_words": len(words), **info, **measure(model, set(words), english, offensive, codes),
              "seconds": round(time.time() - start, 1), **(extra or {})}
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"{name}.json").write_text(json.dumps(result, indent=1))
    (RESULTS / f"{name}.model.json.xz").write_bytes(lzma.compress(json.dumps(model).encode()))
    print(f"{name}: {result['chars']} chars, offensive en {result['offensive_whole_english_list_pct']}% "
          f"own {result['offensive_whole_own_list_pct']}% major {result['offensive_whole_major_lists_pct']}% "
          f"any {result['offensive_whole_pct']}% inside5 "
          f"{result['offensive_inside5_pct']}%, consonant runs {result['consonant_runs_pct']}%, "
          f"relaxed {result['relaxed_rows']}, {result['seconds']}s", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="*", help="language codes, or mixes like zu+tr")
    parser.add_argument("--no-english", action="store_true", help="drop words that are also English words")
    parser.add_argument("--english-baseline", action="store_true")
    parser.add_argument("--blocklist", action="store_true",
                        help="ban tokens that spell terms from the major languages', own languages' and severe English lists")
    args = parser.parse_args()
    english = english_words()
    offensive = load_offensive()
    def banned_for(codes):
        if not args.blocklist:
            return None
        global SEVERE
        SEVERE = SEVERE if SEVERE is not None else load_severe()
        return {t for t, langs in offensive.items() if " " not in t and langs & (MAJOR | set(codes))} | SEVERE

    if args.english_baseline:
        label = "en-v5" + ("-block" if args.blocklist else "")
        run(label, sorted(english), english, offensive, {"languages": ["en"], "blocklist": args.blocklist}, banned_for(["en"]))
    for name in args.names:
        codes = name.split("+")
        exclude = english if args.no_english else frozenset()
        per = MAX_WORDS // len(codes)
        words = list(dict.fromkeys(w for code in codes for w in load_words(code, per, exclude)))
        label = name + ("-noen" if args.no_english else "") + ("-block" if args.blocklist else "")
        try:
            run(label, words, english, offensive, {"languages": codes, "no_english": args.no_english,
                                                    "blocklist": args.blocklist}, banned_for(codes))
        except Exception as error:  # noqa: BLE001  one language failing must not stop the batch
            print(f"{label}: FAILED {error!r}", flush=True)
            (RESULTS / f"{label}.json").write_text(json.dumps({"name": label, "failed": repr(error)}))


if __name__ == "__main__":
    main()
