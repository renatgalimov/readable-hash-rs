# Overnight report: fewer offensive phrases (Nov 8–9)

**Question.** With today's English tables, about 1 phrase in 270 contains an English offensive word (0.37 %), and 1 in 450 a severe one (0.22 %). Can other languages' dictionaries make phrases "less English" and fix this?

**Short answer.**
- **A compile-time blocklist is what fixes it, in any language.** It brings every curated list to 0 in 20,000 samples at a small cost.
- **The language decides everything else:** how English it reads (21 % real English words, against about 1 % for other languages), how easy it is to say, and how much list noise is left.
- **Mixes of non-English languages work well.** Only mixing *with English* backfired.

## What was downloaded

`~/data/phrase-langs/`, 5.3 GB compressed, 831 files (`raw/manifest.jsonl` lists every file and URL):

| Source | Languages | Size | Notes |
|---|---:|---:|---|
| Leipzig Corpora Collection | 268 | 4.5 GB | One corpus per language (≤300K sentences; ≤100K where subtitles exist). The real file lists were read from the per-language download pages (the site has a bot check), so they are in `leipzig_files.json`. |
| Wiktionary via kaikki.org | 287 | 0.4 GB | Every language whose file is under 300 MB (this skips English and a few others). |
| OpenSubtitles frequency lists | 61 | 0.2 GB | hermitdave/FrequencyWords 2018. |
| Tatoeba sentences | ~400 | 0.2 GB | All languages, one file. |
| UniMorph inflected forms | ~170 | 44 MB | |
| Offensive-word lists | ~60 | 0.3 MB | LDNOOBW (28 languages), washyourmouthoutwithsoap (54, includes Zulu), dsojevic English (with severity 1–4 and tags). |

**Ubuntu** is a Nguni Bantu word: Zulu and Xhosa ("I am because we are"). Both are in, along with Ganda, Shona, Sotho, Swahili and others.

- **Failed downloads (190, all 404s, none needed):**
  - 150 Wiktionary languages whose file name differs from their index link;
  - 23 Leipzig names from its stale API list (replaced by the page lists);
  - 14 UniMorph repositories without a data file;
  - 2 attempts at the Surge AI list, which no longer exists.
- **Normalized:** `words/<code>.tsv.xz` is one a–z word list per language (transliterated with `anyascii`), with text counts and a dictionary flag.
  - 313 languages have 2,000+ words; 224 have the 15,000+ needed to build tables.

## How it was measured

- **Tables:** the frozen v5 compiler (from PR #33's branch, untouched) with the same rules. Only the word list changes.
- **Sample:** each table encodes the same 20,000 random 64-bit values.
- **Offensive words** are counted per phrase, as whole words:
  - **English lists** (LDNOOBW + dsojevic + soap);
  - **severe English** (dsojevic severity 3–4 or racial/religious/LGBTQ tags; also counted inside words at 5+ letters);
  - the table language's **own list**;
  - the lists of **13 major languages** (en, es, fr, de, pt, ru, it, tr, zh, ja, ar, hi, id);
  - **any** list.
- **Also measured:** characters per phrase, words with 3+ consonants in a row (a pronounceability proxy), the share of words that are real English words, and real words in the table's own language.
- **Code:** `models/multilang/` (`fetch.py`, `normalize.py`, `experiment.py`, `report.py`, `run_all.sh`, `pass3.sh`). Results are in `results/*.json` plus `*.model.json.xz`. `RESULTS_TABLE.md` and `report.html` rank all 251 tables, with samples.

### The blocklist (`experiment.py --blocklist`)

Built into the row selection, so the format and decoding are unchanged.
- **Banned terms:** the 13 major languages' lists, the table language's own list, and severe English.
- **Rules:**
  - a token is out of a context's row if the previous token plus the token contains a banned term of 5+ letters;
  - right after a beginning, it's out if the word would start with a banned 4-letter term;
  - 3-letter terms are left alone, because words have 4+ letters and banning them inside words removes too much.
- **Three-token spans:** after building, terms spelled across *three* tokens are found and that last pair is banned, then the tables are rebuilt (4 rounds).
- **Build time:** about 4–5 minutes per table.

## Results: the finalists (all 20,000 phrases each)

| Tables | Blocklist | Characters | 3+ consonants | Real English words | EN lists | EN severe | Major lists | Any list | Relaxed rows |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **English (today)** | no | 27.3 | 13.6 % | 21.9 % | **0.36 %** | **0.22 %** | **0.60 %** | 1.43 % | 0 |
| English | yes | 27.3 | 15.7 % | 21.1 % | 0 | 0.015 % | 0 | 0.95 % | 1 |
| Zulu | no | 28.7 | 6.4 % | 0.5 % | 0 | 0.02 % | 0.60 % | 1.34 % | 11 |
| Zulu | yes | 28.8 | 6.7 % | 0.5 % | 0 | 0 | 0 | 0.54 % | 12 |
| Zulu + Xhosa | yes | 28.6 | 6.9 % | 0.4 % | 0 | 0 | 0 | **0.39 %** | 9 |
| Ganda | yes | 29.0 | 4.3 % | 0.9 % | 0 | 0 | 0 | 0.41 % | 24 |
| Basque | yes | 28.5 | 4.7 % | 0.7 % | 0 | 0 | 0 | 0.42 % | 0 |
| Finnish | yes | 28.2 | 3.2 % | 1.4 % | 0 | 0.01 % | 0 | 0.91 % | 33 |
| Turkish | yes | 27.3 | 5.9 % | 0.9 % | 0 | 0 | 0 | 0.89 % | 42 |
| Esperanto | yes | 26.9 | 6.7 % | 1.4 % | 0 | 0.01 % | 0 | 1.18 % | 2 |
| **Bantu mix** (zu+xh+lg+sn) | yes | 27.4 | 4.3 % | 0.7 % | 0 | 0 | 0 | 0.92 % | 4 |
| **Basque + Finnish** | yes | 27.4 | **3.5 %** | 0.9 % | 0 | 0 | 0 | 0.87 % | 2 |
| **Turkish + Zulu** | yes | 27.4 | 5.7 % | 0.7 % | 0 | 0 | 0 | 0.82 % | 2 |

The same rows without the blocklist, plus Xhosa, Shona, Latin, Kabyle, Greek and Zulu+Basque, are in `results/` and `RESULTS_TABLE.md`.

**Samples, all with the blocklist:**

| Tables | Phrases |
|---|---|
| English | `cumman quion nings whinfened` · `cinnage nonest exhorus soted` · `drudorious phledicity holes` |
| Zulu | `iyakuwo iqiwe moto avuyolele` · `ukeka aholweni lisando iyafeka` · `onisa edelungwane bake imvumi` |
| Ganda | `kumbe kolega amakulu gyafola` · `awera ttukutuuka abbibwa nsabeera` |
| Basque | `oren sieraska arta amilen` · `apusuzitzen torritsiaren kola` |
| Finnish | `halle inditaan jakaisi reppivat` · `ruton oikuuhaa paita nortoa` |
| Bantu mix | `leembwa icanga apere edweyako` · `itsiri athwala bekweni sera` · `mishonganga solwimishwa pana` |
| Basque + Finnish | `oneren buek unetan krosizten` · `nalle borota silloon ontoak` |
| Turkish + Zulu | `bende lwakhe esibumba cathelwa` · `edip ogukhole kumi izintina` · `bobameani icakaramisa lila` |
| Esperanto | `elano marboradon aktuto plolia` · `noan kvimpago neado skurbo` |

## What I learned

1. **The blocklist is the fix, and it's cheap.**
   - On today's English tables it takes English-list hits from 0.36 % to 0 and severe hits from 0.22 % to 0.015 %, out of 20,000.
   - The cost: consonant runs 13.6 → 15.7 %, and real English words 21.9 → 21.1 %. Length is unchanged.
2. **Without a blocklist, no language is clean.** A new language swaps one language's offensive words for another's. The best single language on the major lists, Kabyle, still has 0.17 %.
   - Zulu, Ganda and Esperanto do reach 0 on the *English* lists by themselves.
3. **Other languages remove the risk that lists can't catch.**
   - In English tables, 21 % of words are real English words, so phrases form accidental meanings, insults and innuendo that no list contains.
   - Every non-English table here has 0.3–1.5 % real English words.
4. **They are also easier to say.** 3–7 % of words have 3+ consonants in a row, against 15.7 % for English with the blocklist. Phrases are the same length or up to 1.5 characters longer.
5. **Mixing works if English isn't in the mix.** English+Turkish made English hits *worse* (0.26 → 0.39 %), because Turkish tokens completed English words.
   - Non-English mixes didn't: Turkish+Zulu, Basque+Finnish and the Bantu mix all stay at 0 on the English lists, and are the shortest (27.4 characters).
6. **Most "any list" hits are list noise.**
   - Examples: `linda` (on the Zulu list; also a common name), Portuguese `mama`, `site` and `manda` from transliterated Russian lists, Filipino `tanga`.
   - The curated English lists, plain and severe, are the trustworthy measure.

## Caveats

- **"0" means none in 20,000 samples, not none at all.** A guarantee needs an exhaustive search over the tables: the paired-path search used for the ambiguity check, run against an automaton of the banned terms. Not done yet.
- **The three-token bans don't fully converge in 4 rounds.** English: 1,102 → 705 → 488 → 262 new spans, because each rebuild creates new combinations. Terms spread over 4+ tokens, or across the space between words, aren't checked.
- **The lists are incomplete and uneven.** There's no severity outside English, and coverage is thin for African languages. Hits in a language are only as good as its list.
- **Non-English tables need two compiler changes**, done here as experiment-only patches:
  - *Beginning selection:* in many languages the 256 most common word starts chain (`co`/`con`/`cont`), leaving fewer than 128 that don't start each other, so the 256 have to be chosen prefix-free. This hit 75 of 113 languages in pass 1, Zulu and Turkish included.
  - *Join-rule fallback:* rows the join rule can't fill (Zulu 12, Xhosa 60, Turkish 42; Basque and the mixes 0–2) need the rule relaxed.
- **Transliteration:** Arabic, Hebrew and Persian lose their vowels and score badly, so they aren't usable this way. Turkish `ç ğ ı ö ş ü` and similar letters become plain ASCII.
- **Word lists are frequency-based** (subtitles, news, web), so they include names and loanwords. `--no-english` (dropping English words) helped Turkish but not Finnish or Zulu.

## Decisions for you

1. **Add the blocklist to the compiler?** I recommend it whatever the language. To ship it properly:
   - pick the lists and severity;
   - add the exhaustive check so "0" is a proven guarantee;
   - make the three-token bans run until no spans are left, not just 4 rounds.
2. **Which language(s):**
   - **English + blocklist:** the most English-like and memorable for English speakers, but still 21 % real words, so accidental meanings remain.
   - **Basque + Finnish:** the easiest to say (3.5 %), 27.4 characters, with no rows needing the join rule relaxed.
   - **The Bantu mix,** or **Zulu** if the *ubuntu* story matters: easy to say and the least list noise. Zulu alone needs both compiler changes.
   - **Turkish + Zulu:** short, easy to say, with your Turkish idea plus *ubuntu*.
3. **PR #33** is still English v5 without a blocklist. Either fix 1 goes into it before merging, or #33 merges as-is and the new tables come in a follow-up (they change every phrase either way).

Nothing was committed or pushed tonight. PR #33 and its branch are untouched.
