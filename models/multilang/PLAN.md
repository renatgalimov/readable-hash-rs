# Overnight: fewer offensive phrases through other languages' word lists

**User's request (Nov 8, evening):** "work overnight on this problem":
- download as many dictionaries/texts as possible, in as many languages as possible (a few GB is ok, compressed);
- include "ubuntu"'s language (Zulu/Xhosa, Nguni Bantu).

**The problem:** with English tables, about 0.3–0.4 % of random phrases contain an English offensive word.

**User's direction:**
- Make phrases sound less English by using other languages' dictionaries.
- Their test showed Turkish alone cut English hits to ~0, while an English+Turkish mix made them worse.

**Constraints:**
- Don't touch PR #33 (`feature/phrase-u64`) or the pushed branches.
- The v5 compiler and rules stay frozen. Experiments only swap its word list; a row that can't be filled under the join rule gets the rule relaxed and is counted.

## Layout

- **Data:** `~/data/phrase-langs/` (not in git).
  - `raw/<source>/` holds compressed downloads; `raw/manifest.jsonl` records every file.
  - `words/<code>.tsv.xz` has one ASCII word list per language (`word, count, in_dictionary`); `words/languages.json` summarizes them.
  - `logs/`.
- **Code (this directory):**
  - `fetch.py` downloads. Sources: OpenSubtitles frequency lists (62 languages), Leipzig corpora (270 languages, from `leipzig_pick.json`), Tatoeba (all), UniMorph (~180), Wiktionary/kaikki (all under 300 MB), offensive lists (LDNOOBW ~28 languages, washyourmouthoutwithsoap 54, dsojevic en with severity).
  - `normalize.py` turns everything into one a–z word list per language. Transliteration uses `anyascii`; the language-code library is `langcodes` (both installed in `~/data/phrase-langs/.venv`).
  - `experiment.py` builds v5 tables per language or mix (`zu+tr`, `--no-english`) and encodes the same 20,000 values. It measures: length, 3+ consonant runs, real words (English, own language), and offensive hits (English list, severe English, own list, 13 major languages' lists, any list, 5+-letter terms inside words).
  - `report.py` ranks the results into `RESULTS_TABLE.md` and `report.html` (with samples).
  - `run_all.sh` runs normalize, then every language with 15k+ words (3 in parallel), then the report.
- **Leipzig's website** is behind a bot check (Anubis). The per-language file lists were read once with the real browser into `~/data/phrase-langs/leipzig_files.json`. The download server itself is open.

## Plan

1. Downloads (in progress).
2. Pass 1 on whatever data is in; pass 2 (`FORCE=1 ./run_all.sh`) once all downloads finish.
3. Mixes of the best non-English languages (mixing English with Turkish backfired; check whether non-English mixes do too).
4. Compile-time blocklist on the best candidates: ban a token in a row if the previous token plus this token contains a listed term. Measure what's left (terms spanning 3+ tokens) and the cost to naturalness.
5. `REPORT.md`: a recommendation with numbers, samples and caveats.

## Baseline (today's English v5 tables)

27.3 characters. Phrases with a whole word from:
- an English list: 0.37 %;
- severe English terms: 0.22 %;
- the major languages' lists: 0.61 %;
- any list: 1.43 % (noisy: `peter` is French for "to fart").

Words with 3+ consonants in a row: 13.6 %.

## Status log

- 23:10: profanity lists in; downloads started.
- 23:3x: Leipzig file lists read via the browser (270 languages, 6,148 files); picks about 4 GB.
- Pass 1 started on subtitles plus partial data.
- 23:3x: `--blocklist` added to `experiment.py`.
  - In a context's row, a token is banned if the previous token plus the token contains a 5+-letter term from the major-language, own-language or severe-English lists, or if a beginning plus the token starts the word with a 4-letter term. 3-letter terms aren't banned.
  - Rows are keyed per context in this mode. A row that can't fill falls back to no bans (`unbanned_rows`).
- **Key finding: the blocklist on today's English tables** (`en-v5-block`). Phrases with a word from:
  - an English list: 0.365 % → **0.01 %**;
  - major languages' lists: 0.605 % → **0.03 %**;
  - severe English terms: 0.22 % → 0.09 %.

  The cost is tiny: 2,234 token pairs banned, real words 21.9 % → 21.5 %, consonant runs and length unchanged, no rows unfillable.
  - The severe terms left span 3 tokens. Next: find 3–4-token spans in the built tables, ban the last pair, and rebuild until none are left.
- 23:4x: three-token bans added (`three_token_spans`, up to 4 rebuild rounds). **English + blocklist + three-token bans:**
  - phrases with English-list words 0.00 %, major lists 0.00 %, severe English 0.015 % (3 of 20,000);
  - cost: 4,791 banned pairs, consonant runs 13.6 → 15.7 %, real words 21.9 → 21.1 %, 1 relaxed row, about 4 minutes to build;
  - the rounds don't fully converge (1102 → 705 → 488 → 262 new spans), because each rebuild makes a few new combinations.
- Pass 1: 75 of 113 languages failed with "not enough prefix-free tokens".
  - Cause: the 256 most common word starts chain (co/con/cont), leaving fewer than 128 prefix-free.
  - Fix, experiment-only: `prefix_free_vocabulary` picks the 256 beginning candidates prefix-free from all word starts; the result is flagged `beginning_fallback`. The shipped compiler would need the same change for these languages.
- Downloads: Leipzig done (268/270 corpora, 4.5 GB). Wiktionary in progress. 5.6 GB total so far.
- Pass 2 (`FORCE=1 ./run_all.sh`) started with all fixes.
- 00:2x: **Pass 2 done.** 313 languages have 2k+ words; 224 built (1 failed: `klr`).
  - No language alone gets the major-list hits near 0. The best is Kabyle at 0.165 % (English: 0.605 %).
  - English-list hits are 0.00 % for Zulu, Ganda, Tajik, Uzbek and Esperanto (English: 0.365 %), with far fewer consonant runs (zu 6.4 %, lg 4.0 %, eu 4.0 %, fi 2.2 %, against en 13.6 %).
  - Many multi-list hits are list noise or transliteration collisions: `linda` (zu list; a name), `mama` (pt), `site` (ru), `tanga` (fil), `manda` (ru). The curated English lists (LDNOOBW-en, dsojevic with severity) are the cleanest signal.
- Pass 3 (`pass3.sh`) started: mixes, `--no-english`, and the blocklist on the finalists.
- **Pass 3 + 3b done:** 251 tables, all finalists at 0 on the English, own and major lists with the blocklist. **`REPORT.md` is written; next is the user's decision** (blocklist, language, PR #33).
- Pitfall: `pgrep -f <name>` inside a waiter script matches the waiter's own command line, so it waits forever. Track PIDs instead.

## Outcome (Nov 9)

The user chose: all languages unless consonant-heavy, plus every language's blocklist, fixed before PR #33 merges.
- Shipped on `feature/phrase-u64` as `7dc9ea9` (format id phrase-v6, same format). The tables come from 100 languages (2,500 words each, at most 10 % consonant runs, plus Zulu and Xhosa) and a 61-language blocklist with an exhaustive Aho-Corasick walk; it converged in 28 rounds.
- On 20k phrases: 25.0 characters, 7.9 % consonant runs, 0.5 % real English words, 0 list hits, 0 strong-English hits inside words. `results/v6-final.json`.
- The code moved to the repo as `models/phrase-corpus/` (`fetch.py`, `normalize.py`, `build_corpus.py`, README with licences). This directory stays as the research record.
- The `sha3` 0.12 breakage is fixed separately in PR #34 (`shake` crate).
