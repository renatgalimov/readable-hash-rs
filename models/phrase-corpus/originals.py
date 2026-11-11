#!/usr/bin/env python3
"""Original spellings of the word list's words, for the explainer game (the tables themselves use ASCII).

normalize.py folds every word to a-z (onların -> onlarin, Verfügung -> verfugung, þing -> thing), so the word lists
no longer know how a word is written. This re-reads the sources, but only for the languages and words in
training-data/phrase-languages.txt.xz (made by build_corpus.py), and keeps each word's most common spelling:

- the spelling (letters and diacritics) with the highest count over all sources, where a dictionary form counts 1;
- its capitalization from where case means something: words inside Tatoeba sentences and dictionary forms
  (Abend, Nazgûl, onların), the most common form there. A word's first letter is capitalized at the start of a
  sentence, so the frequency lists can't tell "Onların" from "onların". Words never seen there are capitalized
  only if the sources that keep case (not the lowercase subtitle lists) almost never write them in lowercase
  (under LOWERCASE_SHARE).

Writes training-data/phrase-originals.txt.xz: `code<TAB>folded=original folded=original ...`, only for words whose
original differs from the folded form. Its first line, `*<TAB>ö=o ß=ss ı=i ...`, folds each letter the originals
use, so the game can mark a token's letters inside the original spelling (folding letter by letter gives the
folded word; this is checked).

    .venv/bin/python models/phrase-corpus/originals.py     # after build_corpus.py; reads ~/data/phrase-langs/raw
"""
import collections
import json
import lzma
from pathlib import Path

import normalize
from anyascii import anyascii

ROOT = Path(__file__).resolve().parents[2]
LOWERCASE_SHARE = 0.1  # a word seen in lowercase at least this often is shown in lowercase
OUT = ROOT / "models" / "training-data"


class Spellings:
    """Collects original forms of the wanted words of one language group (a stand-in for normalize.Language)."""

    def __init__(self, wanted):
        self.wanted = wanted
        self.any_case = collections.defaultdict(collections.Counter)   # folded -> exact form -> count, all sources
        self.with_case = collections.defaultdict(collections.Counter)  # the same, from sources that keep case
        self.inside = collections.defaultdict(collections.Counter)  # inside Tatoeba sentences, or dictionary forms

    def add(self, word, count=1, dictionary=False, source="", sentence_start=False):
        folded = normalize.fold(word)
        if folded not in self.wanted or any("\ue000" <= ch <= "\uf8ff" for ch in word):
            return  # private-use characters: an old font's encoding (some Yoruba text), not letters
        if dictionary or (source == "tatoeba" and not sentence_start):
            self.inside[folded][word] += 1
        weight = 1 if dictionary else max(count, 1)
        self.any_case[folded][word] += weight
        if source != "subtitles":
            self.with_case[folded][word] += weight

    def original(self, folded):
        spelling = collections.Counter()
        for form, count in self.any_case[folded].items():
            spelling[lower(form)] += count
        if not spelling:
            return folded
        best = min(spelling, key=lambda form: (-spelling[form], form))
        inside = {form: count for form, count in self.inside[folded].items() if lower(form) == best}
        if inside:  # the most common case inside sentences; lowercase on a tie
            return min(inside, key=lambda form: (-inside[form], form != best, form))
        cased = {form: count for form, count in self.with_case[folded].items() if lower(form) == best}
        if not cased or cased.get(best, 0) >= LOWERCASE_SHARE * sum(cased.values()):
            return best
        return min(cased, key=lambda form: (-cased[form], form))


def lower(form):
    """Lowercase; Turkish İ becomes i (Python gives i + a combining dot)."""
    return form.lower().replace("i\u0307", "i")


class Groups(dict):
    """normalize.LANGS replacement: member code -> its group's Spellings (or a sink for other languages)."""

    def __init__(self, member_group, spellings):
        super().__init__()
        self.member_group, self.spellings = member_group, spellings

    def __missing__(self, code):
        group = self.member_group.get(code)
        return self.spellings[group] if group else SINK


class Sink:
    def add(self, *args, **kwargs):
        pass


SINK = Sink()


def main():
    manifest = json.loads((OUT / "phrase-words.json").read_text())
    lists = lzma.decompress((OUT / "phrase-languages.txt.xz").read_bytes()).decode().splitlines()
    wanted = {code: set(words.split()) for code, words in (line.split("\t") for line in lists)}
    member_group = {member: code for code, info in manifest["languages"].items() for member in info["codes"]}
    spellings = {code: Spellings(wanted[code]) for code in wanted}
    normalize.LANGS = Groups(member_group, spellings)
    normalize.WANTED = set(member_group)
    for name, source in normalize.SOURCES.items():
        print("reading", name, flush=True)
        source()
    lines, changed, letters = [], 0, set()
    for code in sorted(wanted):
        pairs = []
        for folded in sorted(wanted[code]):
            original = spellings[code].original(folded)
            if original != folded:
                assert "".join(anyascii(ch).lower() for ch in original) == folded, (code, folded, original)
                letters |= {ch for ch in original if not ("a" <= ch <= "z")}
                pairs.append(f"{folded}={original}")
        changed += len(pairs)
        lines.append(f"{code}\t{' '.join(pairs)}\n")
    fold_line = "*\t" + " ".join(f"{ch}={anyascii(ch).lower()}" for ch in sorted(letters)) + "\n"
    (OUT / "phrase-originals.txt.xz").write_bytes(lzma.compress((fold_line + "".join(lines)).encode(), preset=9))
    print(f"{changed} of {sum(map(len, wanted.values()))} words are written differently from their ASCII form")


if __name__ == "__main__":
    main()
