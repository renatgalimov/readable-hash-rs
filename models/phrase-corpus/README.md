# Phrase word list and blocklist

The phrase tables (`models/compile_phrase.py`) are built from two files in `models/training-data/`:

- **`phrase-words.txt.xz`**: 211,647 words, up to 2,500 of the most common words of 4+ letters from each of
  127 languages. A language is left out if more than 10 % of its common words have three or more consonants in
  a row, or if it has fewer than 2,500 such words. Some are always in, whatever their size or consonants:
  Zulu and Xhosa (the languages of *ubuntu*); English (13.7 %), German (27.9 %), Old English and Old Norse;
  and every
  constructed language we have words for (29), from Esperanto, Toki Pona and Klingon to Tolkien's Quenya,
  Sindarin and his smaller languages. `phrase-words.json` lists the languages, their measurements and
  sources, and every language that was left out and why.
- **`phrase-languages.txt.xz`**: the same words by language, most common first. Only the explainer game
  (`game/`) uses it, to show which languages a token comes from.
- **`phrase-originals.txt.xz`**: how each language writes those words, where that differs from the a–z form
  (`onlarin=onların`, `verfugung=Verfügung`, `thing=þing`): the most common spelling over all sources, with
  its capitalization from the sources that keep case. The tokens stay a–z; the game shows the original
  spelling. Its first line folds each letter used (`ı=i ß=ss þ=th`).
- **`blocklist.txt.xz`**: 5,789 offensive words from 61 languages' lists, folded to a–z, with the
  lists each came from. The compiler bans terms of 5+ letters anywhere in a word and 4-letter terms at the
  start of a word. Strong English terms (severity 2–4 or racial slurs on the dsojevic list) are banned
  anywhere at 4 letters and at the start at 3. The compiler checks every word the tables can produce.

Why a mix of languages: with English tables, 21.9 % of the words in phrases are real English words, so
phrases form accidental meanings and insults that no list can catch. This mix gives 0.8 %. Phrases are also
shorter (25.0 characters on average against 27.3) and easier to say (4.8 % of words have 3+ consonants in a
row, against 13.6 %). These numbers come from encoding the same 20,000 random values.

## Rebuilding

The raw downloads are about 5 GB and are not in the repository.

```sh
python3 -m venv ~/data/phrase-langs/.venv
~/data/phrase-langs/.venv/bin/pip install langcodes anyascii
python3 models/phrase-corpus/fetch.py subtitles leipzig tatoeba unimorph profanity kaikki eldamo   # ~/data/phrase-langs/raw
~/data/phrase-langs/.venv/bin/python models/phrase-corpus/normalize.py                     # ~/data/phrase-langs/words
~/data/phrase-langs/.venv/bin/python models/phrase-corpus/build_corpus.py                  # models/training-data
~/data/phrase-langs/.venv/bin/python models/phrase-corpus/originals.py                     # phrase-originals.txt.xz
python3 models/phrase-corpus/language_wikipedia.py                                   # language-wikipedia.json
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
| [Eldamo](https://eldamo.org/) (Paul Strack) | Tolkien's languages: Quenya, Sindarin and 10 smaller ones (words, their inflections, and the words of attested phrases such as the Ring inscription) | CC BY 4.0 |
| [LDNOOBW](https://github.com/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words) | offensive words, 28 languages | CC BY 4.0 |
| [washyourmouthoutwithsoap](https://github.com/thisandagain/washyourmouthoutwithsoap) | offensive words, 54 languages | CC BY 4.0 |
| [dsojevic/profanity-list](https://github.com/dsojevic/profanity-list) | English offensive words with severity | MIT |

`language-wikipedia.json` maps each language code the game names to its English Wikipedia article, for links.
`language_wikipedia.py` builds it from Wikidata's ISO 639 codes (`vro` is set by hand: Wikidata also gives the wider
South Estonian group).

Words are transliterated with [anyascii](https://github.com/anyascii/anyascii), so non-Latin scripts become
plain a–z (Привет → privet).
