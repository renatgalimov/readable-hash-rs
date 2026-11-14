#!/usr/bin/env python3
"""Build the phrase tables' inputs from the downloaded corpora: a multilingual word list and a blocklist.

Reads the per-language word lists made by normalize.py (~/data/phrase-langs/words/, see fetch.py for the sources)
and writes, under models/training-data/:

- phrase-words.txt.xz: the words the phrase tables are built from. Every language with at least
  WORDS_PER_LANGUAGE words of 4+ letters that isn't consonant-heavy contributes its first WORDS_PER_LANGUAGE in
  ranked_words() order (the most frequent in text, then dictionary forms), so each language counts equally. A
  language is consonant-heavy if more than MAX_CONSONANT_RUNS percent of its first SAMPLE words have three or more
  consonants in a row. The languages in ALWAYS are in whatever their size or consonants (chosen by hand: Zulu and
  Xhosa for "ubuntu"; English, German, Old English, Old Norse and Old High German (10.1 % with its Wiktionary words,
  just over the limit); every constructed language we have words for, from Esperanto to Tolkien's Quenya and
  Klingon). For those, words seen once count too: Tatoeba's sentences are curated, and many constructed languages
  have little other text.
- blocklist.txt.xz: offensive words from every downloaded list, in every language, folded to a-z (`term<TAB>lists`).
  Entries from the English list with severities (dsojevic) are named `dsojevic-en-<severity 1-4>`, plus
  `dsojevic-en-racial` for racial slurs.
- phrase-languages.txt.xz: each language's words, most common first (`code<TAB>word word ...`). Only the
  explainer game uses it, to show which languages a token comes from.
- phrase-words.json: what went in: languages, their measurements, sources and counts, plus the names of the
  languages the offensive-word lists cover (`list_languages`).

    ~/data/phrase-langs/.venv/bin/python models/phrase-corpus/build_corpus.py [--data ~/data/phrase-langs]

It needs the venv from README.md (langcodes, anyascii).
"""
import argparse
import hashlib
import langcodes
import json
import lzma
import re
from pathlib import Path

from anyascii import anyascii

import normalize  # its CONSTRUCTED: one list of constructed languages for both steps

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "models" / "training-data"
WORDS_PER_LANGUAGE = 2_500   # a language's first words of 4+ letters (ranked_words) in the mix; it needs this many
UBUNTU, CHOSEN, CONSTRUCTED = "ubuntu's languages", "chosen", "constructed language"
ALWAYS = {"zu": UBUNTU, "xh": UBUNTU, "en": CHOSEN, "de": CHOSEN, "ang": CHOSEN, "non": CHOSEN, "goh": CHOSEN,
          **{code: CONSTRUCTED for code in normalize.CONSTRUCTED}}
SAMPLE = 5_000               # first words (ranked_words) used to measure consonant runs
MAX_CONSONANT_RUNS = 10.0    # percent of common words with 3+ consonants in a row
RUN = re.compile(r"[^aeiouy]{3,}")
# Codes that name the same language: individual language -> its usual code.
SAME_LANGUAGE = {"ekk": "et", "azj": "az", "swh": "sw", "lvs": "lv", "cmn": "zh", "plt": "mg", "pes": "fa",
                 "zsm": "ms", "nb": "no", "nob": "no", "khk": "mn", "uzn": "uz", "arb": "ar", "quz": "qu"}


def read_words(path):
    """(word, count, in_dictionary) rows, most frequent first (normalize.py writes them that way)."""
    with lzma.open(path, "rt", encoding="utf-8") as lines:
        for line in lines:
            word, count, in_dictionary = line.rstrip("\n").split("\t")
            yield word, int(count), in_dictionary == "1"


def ranked_words(paths, min_count=2):
    """A language's words of 4+ letters: by text frequency, then dictionary-only words in a stable shuffled order.

    The codes of one language add up their counts before min_count applies.
    """
    counts, dictionary = {}, set()
    for path in paths:
        for word, count, in_dictionary in read_words(path):
            if len(word) >= 4:
                counts[word] = counts.get(word, 0) + count
                if in_dictionary:
                    dictionary.add(word)
    counted = {word: count for word, count in counts.items() if count >= min_count}
    dictionary_only = dictionary - counted.keys()
    shuffled = sorted(dictionary_only, key=lambda w: hashlib.sha256(w.encode()).digest())
    return sorted(counted, key=lambda w: (-counted[w], w)) + shuffled


def fold(term):
    return re.sub(r"[^a-z ]", "", anyascii(term).lower()).strip()


def blocklist(raw):
    """{term: sorted list names}: single words from every offensive-word list, folded to a-z."""
    terms = {}

    def add(term, source):
        if (folded := fold(term)) and " " not in folded and len(folded) >= 3:
            terms.setdefault(folded, set()).add(source)

    for path in sorted((raw / "profanity").glob("ldnoobw_*.txt")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            add(line, "ldnoobw-" + path.stem.split("_", 1)[1])
    soap = raw / "profanity" / "washyourmouthoutwithsoap.json"
    for lang, words in json.loads(soap.read_text()).items():
        for word in words:
            add(word, "soap-" + lang)
    for entry in json.loads((raw / "profanity" / "dsojevic_en.json").read_text()):
        for match in entry.get("match", "").split("|"):
            add(match.replace("*", ""), f"dsojevic-en-{entry.get('severity', 1)}")
            if "racial" in entry.get("tags", []):
                add(match.replace("*", ""), "dsojevic-en-racial")
    return {term: sorted(sources) for term, sources in sorted(terms.items())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path.home() / "data" / "phrase-langs")
    args = parser.parse_args()
    languages = json.loads((args.data / "words" / "languages.json").read_text())
    groups = {}
    for code in languages:
        groups.setdefault(SAME_LANGUAGE.get(code, code), []).append(code)
    chosen, skipped, words, by_language = {}, {}, set(), {}
    for code, members in sorted(groups.items()):
        total = sum(languages[m]["words"] for m in members)
        ranked = ranked_words([args.data / "words" / f"{m}.tsv.xz" for m in members], 1 if code in ALWAYS else 2)
        sample = ranked[:SAMPLE]
        rate = round(100 * sum(bool(RUN.search(w)) for w in sample) / max(len(sample), 1), 2)
        info = {"name": languages[members[0]]["name"], "codes": members, "words": total, "consonant_runs_pct": rate,
                "sources": sorted({s for m in members for s in languages[m]["sources"]})}
        if code not in ALWAYS and len(ranked) < WORDS_PER_LANGUAGE:
            skipped[code] = {**info, "reason": "too few words"}
        elif rate > MAX_CONSONANT_RUNS and code not in ALWAYS:
            skipped[code] = {**info, "reason": "consonant-heavy"}
        else:
            taken = ranked[:WORDS_PER_LANGUAGE]
            by_language[code] = taken
            chosen[code] = {**info, "taken": len(taken), **({"included_because": ALWAYS[code]} if code in ALWAYS else {})}
            words.update(taken)
    terms = blocklist(args.data / "raw")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "phrase-words.txt.xz").write_bytes(lzma.compress(("\n".join(sorted(words)) + "\n").encode(), preset=9))
    (OUT / "phrase-languages.txt.xz").write_bytes(lzma.compress(
        "".join(f"{code}\t{' '.join(taken)}\n" for code, taken in sorted(by_language.items())).encode(), preset=9))
    list_codes = sorted({source.split("-")[1] for sources in terms.values() for source in sources})
    list_languages = {code: langcodes.Language.get(code).display_name() for code in list_codes}
    (OUT / "blocklist.txt.xz").write_bytes(lzma.compress(
        "".join(f"{term}\t{','.join(sources)}\n" for term, sources in terms.items()).encode(), preset=9))
    manifest = {"words_per_language": WORDS_PER_LANGUAGE, "always_included": ALWAYS,
                "max_consonant_runs_pct": MAX_CONSONANT_RUNS, "distinct_words": len(words),
                "blocklist_terms": len(terms), "list_languages": list_languages, "languages": chosen,
                "skipped": skipped}
    (OUT / "phrase-words.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(chosen)} languages, {len(words)} distinct words; {len(terms)} blocklist terms; "
          f"skipped {sum(s['reason'] == 'consonant-heavy' for s in skipped.values())} consonant-heavy and "
          f"{sum(s['reason'] == 'too few words' for s in skipped.values())} with too few words")


if __name__ == "__main__":
    main()
