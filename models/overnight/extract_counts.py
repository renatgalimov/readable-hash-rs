#!/usr/bin/env python3
"""Stream a retained gzip JSONL sample into filtered word counts (stdlib only).

Documents are split train/heldout by sha256(id) BEFORE any counting; heldout
documents never contribute to training counts. Output (outside git):
  <lang>_counts.json.gz = {"train": {word: [occurrences, doc_freq]}, "heldout": ...,
                           "stats": {...}}
Filters: NFC; Turkish-aware lowercasing for tr (I->ı, İ->i); alphabet whitelist;
length 2..24; no triple repeated letters; lines repeated in >=5 documents are
dropped as boilerplate; words need doc_freq>=3 in their split (drops most
names/typos/identifiers); words capitalised in >=90% of occurrences are
dropped as likely proper names. Lowercased word counts only are kept.
"""
import gzip
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path("/home/agent/corpora/readable-hash-overnight")
ALPHABETS = {
    "en": set("abcdefghijklmnopqrstuvwxyz"),
    "tr": set("abcçdefgğhıijklmnoöprsştuüvyzâîû"),
}
WORD = re.compile(r"[^\W\d_]+")
TRIPLE = re.compile(r"(.)\1\1")
VERSION = "extract_counts v1"


def lower(text, language):
    if language == "tr":
        text = text.replace("I", "ı").replace("İ", "i")
    return text.lower()


def heldout(doc_id):
    return hashlib.sha256(doc_id.encode()).digest()[0] < 26  # ~10.2%


def documents(language):
    with gzip.open(ROOT / f"{language}_sample.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            yield record["id"], unicodedata.normalize("NFC", record["text"])


def main():
    language = sys.argv[1]
    alphabet = ALPHABETS[language]
    line_docs = Counter()
    for _, text in documents(language):
        line_docs.update({line.strip() for line in text.splitlines() if len(line.strip()) >= 20})
    boilerplate = {line for line, count in line_docs.items() if count >= 5}
    del line_docs
    splits = {"train": (Counter(), Counter(), Counter()), "heldout": (Counter(), Counter(), Counter())}
    stats = Counter()
    for doc_id, text in documents(language):
        occurrences, doc_freq, capitalised = splits["heldout" if heldout(doc_id) else "train"]
        stats["heldout_docs" if heldout(doc_id) else "train_docs"] += 1
        seen = set()
        for line in text.splitlines():
            if line.strip() in boilerplate:
                stats["boilerplate_lines_dropped"] += 1
                continue
            for raw in WORD.findall(line):
                stats["raw_word_tokens"] += 1
                word = lower(raw, language)
                if not 2 <= len(word) <= 24 or not set(word) <= alphabet or TRIPLE.search(word):
                    stats["rejected_word_tokens"] += 1
                    continue
                occurrences[word] += 1
                if raw[0] != word[0]:
                    capitalised[word] += 1
                seen.add(word)
        doc_freq.update(seen)
    result = {"version": VERSION, "language": language, "boilerplate_lines": len(boilerplate)}
    for name, (occurrences, doc_freq, capitalised) in splits.items():
        kept = {word: [count, doc_freq[word]] for word, count in occurrences.items()
                if doc_freq[word] >= 3 and capitalised[word] < 0.9 * count}
        stats[f"{name}_types_before"] = len(occurrences)
        stats[f"{name}_types_kept"] = len(kept)
        stats[f"{name}_occurrences_kept"] = sum(value[0] for value in kept.values())
        result[name] = kept
    result["stats"] = dict(stats)
    with gzip.open(ROOT / f"{language}_counts.json.gz", "wt", encoding="utf-8") as output:
        json.dump(result, output, ensure_ascii=False, sort_keys=True)
    print(json.dumps(result["stats"], indent=1))


if __name__ == "__main__":
    main()
