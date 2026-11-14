# Phrase word list and blocklist

The phrase tables (`models/compile_phrase.py`) are built from two files in `models/training-data/`:

- **`phrase-words.txt.xz`**: 269,509 words: up to 2,500 words of 4+ letters from each of 153 languages.
  A language's words seen most often in text come first. Where text gives fewer than 2,500, dictionary
  forms (Wiktionary, UniMorph, Eldamo) fill the rest, in a fixed pseudo-random order. 53 languages need
  them, and for 51 they are most of the list (Old English, Old Norse, Quenya, ...); 32 have only
  dictionary forms (Old High German, Proto-Slavic, Tolkien's smaller languages, ...). Overall 29 % of the
  words taken are dictionary forms.
  A language is left out if more than 10 % of its first 5,000 words in that order have three or more
  consonants in a row, or if it has fewer than 2,500 words. Some are always in, whatever their size or
  consonants: Zulu and Xhosa (the languages of *ubuntu*); English (13.7 %), German (27.9 %), Old English,
  Old Norse and Old High German; and every constructed language we have words for (29), from Esperanto,
  Toki Pona and Klingon to Tolkien's Quenya, Sindarin and his smaller languages. `phrase-words.json` lists
  the languages, their measurements and sources, and every language that was left out and why.
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
shorter (23.1 characters on average against 27.3) and easier to say (5.1 % of words have 3+ consonants in a
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

`fetch.py` resumes partial downloads and records every file in `raw/manifest.jsonl`. A file gets its final
name only when complete, and `fetch.py` exits with status 1 if anything failed: run it again until it
succeeds before `normalize.py`, which stops at any file it can't read. `leipzig_pick.json` names the Leipzig
corpus taken for each language: the largest of at most 300K sentences, or 100K where a subtitle word list
exists. The names come from the per-language download pages; the API's list is partial. `normalize.py` reads
only those corpora.
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
| [washyourmouthoutwithsoap](https://github.com/thisandagain/washyourmouthoutwithsoap) | offensive words, 54 languages | MIT |
| [dsojevic/profanity-list](https://github.com/dsojevic/profanity-list) | English offensive words with severity | MIT |

`blocklist.txt.xz` contains terms from the two MIT-licensed lists, so it comes with their notices:

- washyourmouthoutwithsoap: Copyright (c) 2018 Andrew Sliwinski.
- dsojevic/profanity-list: Copyright (c) 2021 David Sojevic.

> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
> documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
> rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
> permit persons to whom the Software is furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
> Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
> WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
> COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
> OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

`language-wikipedia.json` maps each language code the game names to its English Wikipedia article, for links.
`language_wikipedia.py` builds it from Wikidata's ISO 639 codes (`vro` is set by hand: Wikidata also gives the wider
South Estonian group).

Words are transliterated with [anyascii](https://github.com/anyascii/anyascii), so non-Latin scripts become
plain a–z (Привет → privet).
