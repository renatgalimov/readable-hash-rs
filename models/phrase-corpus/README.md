# Phrase word list and blocklist

The phrase tables (`models/compile_phrase.py`) are built from two files in `models/training-data/`:

- **`phrase-words.txt.xz`**: 187,020 words, the 2,500 most common words of 4+ letters from each of 100
  languages. A language is left out if more than 10 % of its common words have three or more consonants in a
  row (English has 13.7 %, so English is out), or if it has fewer than 2,500 such words. Zulu and Xhosa, the
  languages of *ubuntu*, are always in. `phrase-words.json` lists the languages, their measurements and
  sources, and every language that was left out and why.
- **`phrase-languages.txt.xz`**: the same words by language, most common first. Only the explainer game
  (`game/`) uses it, to show which languages a token comes from.
- **`blocklist.txt.xz`**: 5,789 offensive words from about 60 languages' lists, folded to a–z, with the
  lists each came from. The compiler bans terms of 5+ letters anywhere in a word and 4-letter terms at the
  start of a word. Strong English terms (severity 2–4 or racial slurs on the dsojevic list) are banned
  anywhere at 4 letters and at the start at 3. The compiler checks every word the tables can produce.

Why a mix of languages: with English tables, 21.9 % of the words in phrases are real English words, so
phrases form accidental meanings and insults that no list can catch. This mix gives 0.5 %. Phrases are also
shorter (25.0 characters on average against 27.3) and easier to say (7.9 % of words have 3+ consonants in a
row, against 13.6 %). These numbers come from encoding the same 20,000 random values.

## Rebuilding

The raw downloads are about 5 GB and are not in the repository.

```sh
python3 -m venv ~/data/phrase-langs/.venv
~/data/phrase-langs/.venv/bin/pip install langcodes anyascii
python3 models/phrase-corpus/fetch.py subtitles leipzig tatoeba unimorph profanity kaikki   # ~/data/phrase-langs/raw
~/data/phrase-langs/.venv/bin/python models/phrase-corpus/normalize.py                     # ~/data/phrase-langs/words
~/data/phrase-langs/.venv/bin/python models/phrase-corpus/build_corpus.py                  # models/training-data
python3 models/compile_phrase.py                                                     # src/phrase_data.rs
```

`fetch.py` resumes partial downloads and records every file in `raw/manifest.jsonl`. `leipzig_pick.json`
names the Leipzig corpus taken for each language: the largest of at most 300K sentences, or 100K where a
subtitle word list exists. The names come from the per-language download pages; the API's list is partial.
Sources change over time, so a rebuild may give different words, and with them different phrases. The
committed files are what the tables are built from.

## Sources

| Source | Used for | Licence |
|---|---|---|
| [Leipzig Corpora Collection](https://wortschatz.uni-leipzig.de/en/download) | word frequencies, 268 languages | CC BY ([terms](https://wortschatz.uni-leipzig.de/en/usage)) |
| [Tatoeba](https://tatoeba.org/en/downloads) | words in example sentences | CC BY 2.0 FR |
| [FrequencyWords](https://github.com/hermitdave/FrequencyWords) (OpenSubtitles 2018) | word frequencies, 61 languages | content CC BY-SA 4.0 |
| [UniMorph](https://unimorph.github.io/) | inflected forms (dictionary words) | per language, mostly CC BY-SA |
| [Wiktionary via kaikki.org](https://kaikki.org/) | dictionary words | CC BY-SA 4.0 / GFDL |
| [LDNOOBW](https://github.com/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words) | offensive words, 28 languages | CC BY 4.0 |
| [washyourmouthoutwithsoap](https://github.com/thisandagain/washyourmouthoutwithsoap) | offensive words, 54 languages | CC BY 4.0 |
| [dsojevic/profanity-list](https://github.com/dsojevic/profanity-list) | English offensive words with severity | MIT |

Words are transliterated with [anyascii](https://github.com/anyascii/anyascii), so non-Latin scripts become
plain a–z (Привет → privet).
