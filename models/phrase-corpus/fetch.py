#!/usr/bin/env python3
"""Download word lists, texts and offensive-word lists for as many languages as possible.

Everything lands compressed under ~/data/phrase-langs/raw/<source>/ (already-compressed archives are kept as they
are; plain text is xz-compressed). The script is resumable: finished files are skipped, partial downloads resume.
A manifest (raw/manifest.jsonl) records every file: source, language, URL, bytes, status.

    python3 models/phrase-corpus/fetch.py [source ...]   # sources: subtitles leipzig tatoeba unimorph profanity kaikki
"""
import json
import lzma
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

DATA = Path.home() / "data" / "phrase-langs"
RAW = DATA / "raw"
MANIFEST = RAW / "manifest.jsonl"
UA = "readable-hash-research/0.1 (one-off corpus download; contact renat2017@gmail.com)"


def log(*parts):
    print(time.strftime("%H:%M:%S"), *parts, flush=True)


def record(**entry):
    with MANIFEST.open("a") as out:
        out.write(json.dumps(entry) + "\n")


def done_urls():
    if not MANIFEST.exists():
        return set()
    return {json.loads(line)["url"] for line in MANIFEST.open() if '"status": "ok"' in line}


DONE = set()


def fetch(source, lang, url, dest, compress=False):
    """Download url to dest (resuming); xz-compress plain text when asked. Returns the final path or None."""
    final = dest.with_name(dest.name + ".xz") if compress else dest
    if url in DONE and final.exists():
        return final
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    result = subprocess.run(["curl", "-sS", "-L", "-f", "--retry", "3", "--retry-delay", "5", "-m", "3600",
                             "-A", UA, "-C", "-", "-o", str(part), url], capture_output=True, text=True)
    if result.returncode != 0:
        record(source=source, lang=lang, url=url, status="failed", error=result.stderr.strip()[-200:])
        log("FAIL", source, lang, url, result.stderr.strip()[-120:])
        part.unlink(missing_ok=True)
        return None
    if compress:
        with part.open("rb") as raw, lzma.open(final, "wb", preset=6) as packed:
            while chunk := raw.read(1 << 20):
                packed.write(chunk)
        part.unlink()
    else:
        part.rename(final)
    size = final.stat().st_size
    record(source=source, lang=lang, url=url, path=str(final.relative_to(DATA)), bytes=size, status="ok")
    DONE.add(url)
    log("ok", source, lang, f"{size / 1e6:.1f} MB", final.name)
    time.sleep(0.5)  # be polite
    return final


def get_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def subtitles():
    """OpenSubtitles 2018 word frequency lists (hermitdave/FrequencyWords): ~62 languages."""
    langs = [entry["name"] for entry in get_json("https://api.github.com/repos/hermitdave/FrequencyWords/contents/content/2018")]
    for lang in langs:
        base = f"https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/{lang}/{lang}"
        if not fetch("subtitles", lang, f"{base}_full.txt", RAW / "subtitles" / f"{lang}_full.txt", compress=True):
            fetch("subtitles", lang, f"{base}_50k.txt", RAW / "subtitles" / f"{lang}_50k.txt", compress=True)


def leipzig():
    """Leipzig Corpora Collection: one corpus per language (~270 languages), each with a word frequency list.

    leipzig_pick.json (made from the per-language download pages, which list the real file names) holds the
    choice: the largest corpus of at most 300K sentences, or 100K where OpenSubtitles already covers the language.
    Without it, fall back to the API's (partial, partly stale) corpus list.
    """
    picks = Path(__file__).resolve().parent / "leipzig_pick.json"
    if picks.exists():
        for lang, name in sorted(json.loads(picks.read_text()).items()):
            fetch("leipzig", lang, f"https://downloads.wortschatz-leipzig.de/corpora/{name}.tar.gz", RAW / "leipzig" / f"{name}.tar.gz")
        return
    corpora = get_json("https://api.wortschatz-leipzig.de/ws/corpora/availableCorpora?limit=2000")
    best = {}
    for corpus in corpora:
        lang = corpus["corpusName"].split("_")[0].split("-")[0]
        size = corpus["numberOfSentences"] or 0
        if size <= 300_000 and size > best.get(lang, ("", 0))[1]:
            best[lang] = (corpus["corpusName"], size)
    for lang, (name, _) in sorted(best.items()):
        fetch("leipzig", lang, f"https://downloads.wortschatz-leipzig.de/corpora/{name}.tar.gz", RAW / "leipzig" / f"{name}.tar.gz")


def tatoeba():
    """Tatoeba: every sentence in every language, one file (~220 MB bz2)."""
    fetch("tatoeba", "all", "https://downloads.tatoeba.org/exports/sentences.tar.bz2", RAW / "tatoeba" / "sentences.tar.bz2")


def unimorph():
    """UniMorph: inflected word forms for ~180 languages (one GitHub repo per language)."""
    repos, page = [], 1
    while True:
        batch = get_json(f"https://api.github.com/orgs/unimorph/repos?per_page=100&page={page}")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    for repo in repos:
        name = repo["name"]
        if len(name) != 3 or not name.isalpha():
            continue  # language repos are named by ISO 639-3 code
        branch = repo.get("default_branch", "master")
        fetch("unimorph", name, f"https://raw.githubusercontent.com/unimorph/{name}/{branch}/{name}",
              RAW / "unimorph" / f"{name}.tsv", compress=True)


def profanity():
    """Offensive-word lists: LDNOOBW (~28 languages), washyourmouthoutwithsoap (~50), dsojevic (en, with severity)."""
    for entry in get_json("https://api.github.com/repos/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words/contents"):
        name = entry["name"]
        if entry["type"] == "file" and "." not in name and name not in ("LICENSE", "USERS"):
            fetch("profanity", name, entry["download_url"], RAW / "profanity" / f"ldnoobw_{name}.txt")
    fetch("profanity", "multi", "https://raw.githubusercontent.com/thisandagain/washyourmouthoutwithsoap/develop/data/build.json",
          RAW / "profanity" / "washyourmouthoutwithsoap.json")
    fetch("profanity", "en", "https://raw.githubusercontent.com/dsojevic/profanity-list/main/en.json", RAW / "profanity" / "dsojevic_en.json")
    for branch in ("main", "master"):
        if fetch("profanity", "en", f"https://raw.githubusercontent.com/surge-ai/profanity/{branch}/profanity_en.csv",
                 RAW / "profanity" / "surge_en.csv"):
            break


def kaikki():
    """Wiktionary word lists (kaikki.org): one JSONL per language; only languages whose file is under ~300 MB."""
    try:
        index = urllib.request.urlopen(urllib.request.Request("https://kaikki.org/dictionary/", headers={"User-Agent": UA}),
                                       timeout=60).read().decode()
    except Exception as error:  # noqa: BLE001
        record(source="kaikki", lang="all", url="https://kaikki.org/dictionary/", status="failed", error=str(error)[:200])
        log("FAIL kaikki index", error)
        return
    import re
    for path, lang in sorted(set(re.findall(r'href="(([A-Z][A-Za-z%0-9-]+)/index\.html)"', index))):
        name = urllib.parse.unquote(lang)
        url = f"https://kaikki.org/dictionary/{lang}/kaikki.org-dictionary-{lang}.jsonl"
        head = subprocess.run(["curl", "-sI", "-L", "-m", "60", "-A", UA, url], capture_output=True, text=True).stdout
        sizes = [int(line.split(":")[1]) for line in head.lower().splitlines() if line.startswith("content-length")]
        if not sizes or sizes[-1] > 300_000_000:
            continue
        fetch("kaikki", name, url, RAW / "kaikki" / f"{name}.jsonl", compress=True)


SOURCES = {"profanity": profanity, "subtitles": subtitles, "leipzig": leipzig, "tatoeba": tatoeba,
           "unimorph": unimorph, "kaikki": kaikki}

if __name__ == "__main__":
    import urllib.parse  # noqa: F401  (used by kaikki)
    RAW.mkdir(parents=True, exist_ok=True)
    DONE.update(done_urls())
    for name in sys.argv[1:] or list(SOURCES):
        log("== source", name)
        try:
            SOURCES[name]()
        except Exception as error:  # noqa: BLE001  keep going with the other sources
            log("SOURCE FAILED", name, repr(error))
            record(source=name, lang="-", url=name, status="failed", error=repr(error)[:300])
    total = sum(f.stat().st_size for f in RAW.rglob("*") if f.is_file())
    log(f"== all done: {total / 1e9:.2f} GB under {RAW}")
