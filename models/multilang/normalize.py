#!/usr/bin/env python3
"""Turn every downloaded source into one plain a-z word list per language.

For each language (normalized code, e.g. "zu"), words/<code>.tsv.xz holds `word<TAB>count<TAB>in_dictionary`:
- count sums real-text frequencies (OpenSubtitles lists, Leipzig word lists, words in Tatoeba sentences);
- in_dictionary is 1 if a dictionary source (UniMorph forms, Wiktionary/kaikki entries and forms) has the word.
Words are transliterated to ASCII with anyascii (Привет -> privet, çğış -> cgis), lowercased, and kept only if
they are 2+ letters a-z. words/languages.json summarizes each language: name, sources, word counts and how much of
it was originally Latin script.

    .venv/bin/python normalize.py            # all sources found under raw/
"""
import collections
import csv
import io
import json
import lzma
import re
import sys
import tarfile
import unicodedata
from pathlib import Path

import langcodes
from anyascii import anyascii

DATA = Path.home() / "data" / "phrase-langs"
RAW, WORDS = DATA / "raw", DATA / "words"
WORD = re.compile(r"\w+", re.UNICODE)
ASCII_WORD = re.compile(r"[a-z]{2,}")
NO_SPACES = {"zh", "ja", "th", "lo", "km", "my", "bo", "yue", "wuu"}  # scripts without spaces between words
csv.field_size_limit(sys.maxsize)


def code_of(raw):
    """Normalize a code or a language name to a short tag ('zul' -> 'zu', 'Zulu' -> 'zu'); None if unknown."""
    raw = raw.replace("_", "-")
    try:
        tag = langcodes.get(raw) if raw[:1].islower() else langcodes.find(raw)
    except (LookupError, ValueError, langcodes.tag_parser.LanguageTagError):
        return None
    return tag.language if tag.language and tag.is_valid() else None


def fold(word):
    """ASCII form of a word, or None if it isn't 2+ letters a-z afterwards."""
    if not any(unicodedata.category(ch).startswith("L") for ch in word):
        return None
    ascii_form = anyascii(word).lower()
    return ascii_form if ASCII_WORD.fullmatch(ascii_form) else None


class Language:
    def __init__(self):
        self.count = collections.Counter()
        self.dictionary = set()
        self.sources = set()
        self.latin = self.total = 0

    def add(self, word, count=1, dictionary=False, source=""):
        folded = fold(word)
        if not folded:
            return
        self.total += 1
        self.latin += word.isascii() or all(unicodedata.name(ch, "").startswith("LATIN") for ch in word if ch.isalpha())
        if dictionary:
            self.dictionary.add(folded)
        else:
            self.count[folded] += count
        self.sources.add(source)


LANGS = collections.defaultdict(Language)


def subtitles():
    for path in sorted((RAW / "subtitles").glob("*.txt.xz")):
        lang = path.name.split("_")[0]
        if lang == "ze":
            continue  # mixed English-Chinese subtitles
        code = code_of(lang)
        if not code:
            continue
        with lzma.open(path, "rt", encoding="utf-8", errors="replace") as lines:
            for line in lines:
                parts = line.split()
                if len(parts) == 2 and parts[1].isdigit():
                    LANGS[code].add(parts[0], int(parts[1]), source="subtitles")


def leipzig():
    for path in sorted((RAW / "leipzig").glob("*.tar.gz")):
        code = code_of(path.name.split("_")[0].split("-")[0])
        if not code:
            continue
        try:
            with tarfile.open(path) as archive:
                member = next((m for m in archive.getmembers() if m.name.endswith("-words.txt")), None)
                if member is None:
                    continue
                for line in io.TextIOWrapper(archive.extractfile(member), encoding="utf-8", errors="replace"):
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) >= 3 and parts[-1].isdigit():
                        LANGS[code].add(parts[1], int(parts[-1]), source="leipzig")
        except (EOFError, tarfile.TarError, OSError) as error:
            print("  skipped", path.name, repr(error)[:80], flush=True)


def tatoeba():
    path = RAW / "tatoeba" / "sentences.tar.bz2"
    if not path.exists():
        return
    cache = {}
    with tarfile.open(path) as archive:
        member = next(m for m in archive.getmembers() if m.name.endswith(".csv"))
        for row in csv.reader(io.TextIOWrapper(archive.extractfile(member), encoding="utf-8", errors="replace"),
                              delimiter="\t", quoting=csv.QUOTE_NONE):
            if len(row) < 3:
                continue
            if row[1] not in cache:
                cache[row[1]] = code_of(row[1]) if row[1] != "\\N" else None
            code = cache[row[1]]
            if not code or code in NO_SPACES:
                continue
            for word in WORD.findall(row[2]):
                LANGS[code].add(word, source="tatoeba")


def unimorph():
    for path in sorted((RAW / "unimorph").glob("*.tsv.xz")):
        code = code_of(path.name.split(".")[0])
        if not code:
            continue
        try:
            with lzma.open(path, "rt", encoding="utf-8", errors="replace") as lines:
                for line in lines:
                    parts = line.rstrip("\n").split("\t")
                    for field in parts[:2]:
                        for word in field.split():
                            LANGS[code].add(word, dictionary=True, source="unimorph")
        except (EOFError, lzma.LZMAError, OSError) as error:
            print("  skipped", path.name, repr(error)[:80], flush=True)


def kaikki():
    for path in sorted((RAW / "kaikki").glob("*.jsonl.xz")):
        try:
            kaikki_file(path)
        except (EOFError, lzma.LZMAError, OSError) as error:
            print("  skipped", path.name, repr(error)[:80], flush=True)


def kaikki_file(path):
    if True:
        with lzma.open(path, "rt", encoding="utf-8", errors="replace") as lines:
            for line in lines:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                code = code_of(entry.get("lang_code", "") or entry.get("lang", ""))
                if not code:
                    continue
                for word in [entry.get("word", "")] + [form.get("form", "") for form in entry.get("forms", [])]:
                    for part in word.split():
                        LANGS[code].add(part, dictionary=True, source="kaikki")


def main():
    WORDS.mkdir(parents=True, exist_ok=True)
    for source in (subtitles, leipzig, tatoeba, unimorph, kaikki):
        print("reading", source.__name__, flush=True)
        try:
            source()
        except (EOFError, lzma.LZMAError, tarfile.TarError, OSError) as error:
            # a file still being downloaded or compressed by fetch.py; the next run picks it up
            print("  skipped the rest of", source.__name__, "after", repr(error)[:120], flush=True)
    summary = {}
    for code, lang in sorted(LANGS.items()):
        words = set(lang.count) | lang.dictionary
        if len(words) < 2000:
            continue
        with lzma.open(WORDS / f"{code}.tsv.xz", "wt", encoding="utf-8") as out:
            for word in sorted(words, key=lambda w: (-lang.count.get(w, 0), w)):
                out.write(f"{word}\t{lang.count.get(word, 0)}\t{int(word in lang.dictionary)}\n")
        summary[code] = {"name": langcodes.get(code).display_name(), "words": len(words),
                         "text_words": len(lang.count), "dictionary_words": len(lang.dictionary),
                         "sources": sorted(lang.sources), "latin_share": round(lang.latin / max(lang.total, 1), 3)}
    (WORDS / "languages.json").write_text(json.dumps(summary, indent=1))
    print(f"{len(summary)} languages with 2000+ words")


if __name__ == "__main__":
    main()
