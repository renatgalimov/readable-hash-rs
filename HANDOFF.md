**Archived (Nov 10).** The user chose the 10-token format (phrase-v7) as the only one: it is `readable_hash::encode_u64`/`decode_u64` on `feature/phrase-u64` (PR #33). Everything else is archived:
- this branch: the early experiments (v2–v5, dyn, lenmin, the toy spaces game) and the multilingual research in `models/multilang/` (scripts, reports, per-language result summaries; the per-language `*.model.json.xz` tables are left out, `run_all.sh` rebuilds them from `~/data/phrase-langs/`). Tag `archive/phrase-experiments`.
- tag `archive/phrase-11-tokens`: the 11-token format (phrase-v6) with its Rust codec, as PR #33 had it before the switch.
- tag `archive/phrase-9-tokens`: the 9-token prototype (256/64/64 lists, a 2–4-bit layout code) and its game.

**Nov 8–9 overnight:** the offensive-phrase research is in `models/multilang/` (`REPORT.md` is the summary, `PLAN.md` the log; data in `~/data/phrase-langs/`, 5.3 GB).
- Finding: a compile-time blocklist fixes it in any language.
- The language choice (English, Basque+Finnish, Bantu mix, Zulu, Turkish+Zulu) is the user's call.
- PR #33 is untouched.

# HANDOFF (superseded: v5 shipped on its own branch)

**Nov 8, user: "this is what I wanted… commit, push to a branch, make it a proper feature, the default implementation".**
- `feature/phrase-u64` (worktree `~/projects/readable-hash-rs-phrase`, commit `50b7200`, based on `main` `ed08744`) is the clean feature. It is pushed, and a PR against `main` was requested (needs approval at the IAP gateway).
  - v5 is `readable_hash::encode_u64`/`decode_u64` (module `phrase`).
  - Files: `src/phrase{,_data}.rs`, `models/compile_phrase.py`, `phrase_model.json`, `phrase_report.json`, `test_phrase.py`, `examples/phrase.rs`, `tests/features/phrase.feature`, `game/` (build writes `game/space-game.html`, gitignored; the check runs from `file://` and exits non-zero on failure).
- This branch (`feature/reversible-u64`, commit `a89a4fc`) is the pushed snapshot of all experiments, including this file.
- Blog: `post/bits-in-the-spaces` in `~/projects/renatgalimov`, commit `1a3abed`, pushed. Two draft posts plus the game pages.
  - `readable-hash-0-11.md` still describes an older design: a scramble, ≤24 characters, `42` = `drumlot forfelizo dakwey`. The user was told.
- Pre-existing on `main`: `--all-features` fails to build since `sha3` 0.12 (#23). CI Lint uses `--all-features`.

# Handoff: the spaces game

**Intent: finish the spaces game.** It is an interactive explainer for the blog post "The bits are in the spaces". The player builds one phrase choice by choice, while a gauge of 64 small squares fills with the bits each choice stores. The game uses a toy token model. The real Rust encoder is not part of this work and stays untouched.

> **Latest: see "Session 3, final" below.** No short words; the layout is a 5-bit pick of 32, and phrases are 66 or 68 bits. Next comes designing the token-picking pages.

This file is in `readable-hash-rs-reversible`, the working clone of `renatgalimov/readable-hash-rs`. The clone `/home/agent/projects/readable-hash-rs` is pristine `main`; nothing was done there.

## Files

| What | Path |
|---|---|
| Game source (edit this) | `game/space-game.template.html` |
| Build script | `game/build_space_game.py`. It injects the token pools from `models/phrase_v3_model.json` and `models/training-data/english-lowercase.txt`. |
| Generated game (don't edit) | `/home/agent/projects/renatgalimov/blog/static/diagrams/space-game.html` |
| Frozen first version (16 layouts, 10 tokens) | `blog/static/diagrams/space-game-v1.html`, source `game/space-game-v1.template.html` |
| Blog post (draft) | `blog/content/posts/bits-in-the-spaces.md`. It doesn't embed the game yet; it shows `static/diagrams/space-layouts.svg`. |
| Release post (draft, wishful) | `blog/content/posts/readable-hash-0-11.md` |

The blog repo is `/home/agent/projects/renatgalimov`, branch `post/bits-in-the-spaces`. Nothing there is committed. `blog/static/style.css` has table CSS appended.

The game sources were copied here from the agent's scratch directory, which is pruned after 24 hours. The copies in `game/` are the canonical ones; building from them gives a byte-identical page.

## Build and preview

```sh
python3 game/build_space_game.py
```

- A Zola server runs with drafts on http://127.0.0.1:1111 (pid 497285, live reload). The game is at http://127.0.0.1:1111/diagrams/space-game.html.
- The Zola binary is `~/.hermes/profiles/senior-architect/cache/scratch/zola` (0.23.4, aarch64). If the scratch directory was pruned, download it again from https://github.com/getzola/zola/releases/download/v0.23.4/zola-v0.23.4-aarch64-unknown-linux-gnu.tar.gz and run, from `blog/`:

  ```sh
  zola serve --drafts --interface 127.0.0.1 --port 1111
  ```
- After a change, test in a real browser: click through every branch, read the `#formula`, `#count` and `#msg` text, check for JS errors, and look at a screenshot.
  - `node game/check_space_game.mjs` does this headlessly. It starts its own Chromium on port 9333 and walks every branch into `$TMPDIR/space-game-check/walk.json`. It also takes 4 screenshots, runs "Fill randomly" and prints any JS errors.
  - The agent's browser tools (`browser_exec`, `browser_cdp`) refuse 127.0.0.1, so use the script.

## How the user wants it built

- **One page at a time.** The user designs each step and confirms it. Confirmed pages are frozen; ask before changing them. Step 1, "length of the first word", was confirmed early (1–4 tokens, 2 bits). Later designs may change what counts as step 1, so confirm with the user.
- **Explain every page:** what the last choice cost, which options are left and why, and what this choice is worth (log₂ of the number of options).
- **A colour key is always shown,** with each colour's number of choices and bits. Green: short word, 32 choices, 5 bits. Black: beginning, …; orange: length or layout choices.
- **Count bits honestly.** As soon as a word's length is chosen, the gauge also counts the bits its tokens will take (shown pale). Bits beyond 64 appear as "spare"; a shortfall gets a dashed orange box.
- **Short words:** a single token from a fixed list of 2–3 letter words. A short word is never last in the phrase and never next to another short word. No *a*/*an*, because a spelling variant must not carry bits.
- **Decoding is exact.** The fixed total token count tells the decoder how to read the phrase (e.g. *the* is a short word, not `th`+`e`).
- **The user's goal for this design:** consume as many bits as possible on layout (spaces) before building words, with little surplus.
- No commits, pushes or merges; posts stay `draft = true`. Use Sonnet 5.5 (`claude-sonnet-5-5`, provider `anthropic`) for programmer delegation, not Opus.

## What the game does now

- **Phrase:** 11 tokens, 3 words. The first word is 1–4 tokens and the second 2–6; the third takes what's left, so its length adds 0 bits.
- **Pages built:** the first-word length; the second-word length (for all 4 branches); a summary page. Token picking is **not designed yet**; the summary ends with "Picking the tokens isn't designed yet."
- **Pools in the build script:**
  - short words: 32 (`at by if in is my no of on or so to up we the and for but not our his her its all any few one two ten new old big`);
  - beginnings: 64 (the most frequent word starts);
  - middles: 64;
  - endings: 16 (`ing ed er es ly al ion ous ble ic an en on ness y s`).
- **Totals by first word:** 1 → 64.58, 2 → 64, 3 → 64.32, 4 → 64.

**This is already out of date.** The user then asked for 128 beginnings and 32 endings, and moved to the layout-first design below.

## Session 2 (Nov 8): pools done, layout rule given

- **Pools are implemented** in `game/build_space_game.py`: 128 beginnings (all the model has, prefix-free), 32 middles, 32 endings, 32 short words. The user confirmed 32 middles.
  - The middles are the model's top 32, with `l` swapped for `bi`.
  - The endings are the old 16 plus `ation le ling ll man ns re rs ry te ted th ting ts um ve`.
  - The build now asserts that no two picks spell the same word, for 0–3 middles. The old pools failed this: `l`+`es` = `le`+`s`.
  - The generated page has the new pools but **still the old 3-word layout logic**.
- **The user's layout rule** (replaces the "Open decisions" 1–2 below):
  - Page 1: first word length 1, 3, 4 or 5 (2 is dropped, so there are 4 options).
  - Page 2: 2, 3, 4 or 5 after a short word; 1, 3, 4 or 5 after a built word. The user wrote "if the first was 2", most likely meaning a built word; ask to confirm.
  - Keep adding pages until the layout is fully chosen, skipping a page when only one option is left.
  - Other limits are unchanged: 11 tokens, at most 4 words, short word never last and never next to another.
- **Not settled yet:**
  - After a first word of 5, the 5 option doesn't fit (it leaves 1 token, and a short word can't be last).
  - Page 3 isn't specified. With the same rule and options that don't fit removed, there are 37 layouts and totals of 64.17–68.58 bits.
  - Variant: fill a gap with 2. That gives 46 layouts and 64.58–69.

## Session 3 (Nov 8): layout pages built

**Decided by the user:**
- After any built word, the options are 1, 3, 4 or 5.
- When a length doesn't fit, **2 fills the gap**.

This supersedes "Design in progress" and "Open decisions" 1–3 below. Middles stay at 32.

**Implemented** in `game/space-game.template.html` (`lengthOptions`, `layout`, `nextStep`):
- Each page offers 1, 3, 4 or 5 tokens, or 2, 3, 4 or 5 right after a short word.
- A length is dropped if no legal phrase can follow it. Then 2 is added if 2 isn't already offered and fits.
- A page with one option is skipped; that word is forced and adds 0 bits.
- Rules: 11 tokens, at most 4 words, a short word never last and never next to another.

**Result:**
- **46 layouts, 64.58–69 bits**, so a phrase never falls short of 64.
- Page 1 and page 2 always have 4 options (2 bits). Page 3 has 1–4. The fourth word is always forced.
- 19 choice pages.
- Totals: 67 ×15, 66.58 ×14, 66 ×6, 65 ×5, 68.58 ×3, 69 ×2, 64.58 ×1.

**Page text:**
- Each page says what the last word cost and how many tokens and words are left.
- It says why each usual length is missing ("would leave a single token, and a short word can't be last", "would leave 7 tokens for the last word, which holds at most 5", "4 and 5 are more than the 3 tokens left"), then "2 fills the gap", then the log₂ worth.
- The orange key row reads "2, 3 or 4 choices / 1, 1.58 or 2 bits".
- The summary explains the forced word and gives the layout and verdict. It still ends "Picking the tokens isn't designed yet."

**Verified:** the browser walk equals a Python enumeration, with all 46 totals equal. No JS errors and no shortfall boxes; "Fill randomly" completes. Screenshots checked.

**Then changed (user): at most one short word per phrase.**
- Once the short word is used, every later page offers 2, 3, 4 or 5 instead of 1, 3, 4 or 5. The code tracks `shortUsed`; it no longer tracks "last word was short".
- **44 layouts, still 64.58–69 bits.** Only `1+4+1+5` and `1+5+1+4` drop out.
- Totals: 66.58 ×19, 67 ×10, 66 ×6, 68.58 ×3, 64.58 ×2, 65 ×2, 69 ×2.
- Page 1 says "with at most one short word".
- Verified the same way: 44 end states equal Python, 19 choice pages, no JS errors.
- The numbers in "Result" above are from before this change.

### Session 3, final: no short words; the layout is exactly 5 bits

**This supersedes everything above about short words, 1/3/4/5 options, "2 fills the gap", 44/46 layouts and per-page log₂(options).**

**The user's decisions:**
- Drop the 1-token short word entirely. Every word is a built word of 2–5 tokens.
- 11 tokens, at most 4 words, gives **32 layouts = 5 bits**: 12 of 3 words and 20 of 4 words.
- The layout is one pick from 32, so **every layout is worth exactly 5 bits**.
- Bit counting is option 2, the weighted share. Each length option is worth log₂(layouts possible ÷ layouts it keeps), and every path adds up to 5.
  - First word: 2 keeps 12 of 32 (1.42 bits), 3 keeps 9 (1.83), 4 keeps 7 (2.19), 5 keeps 4 (3).
  - The user turned down option 1, a single orange 5-bit block that fills as pages are picked.

**Implemented** in the template (`layoutCount`, `lengthOptions`, `nextStep`):
- Buttons show "keeps N of M" and the option's bits.
- The prompt explains the log₂(M ÷ kept) rule. Dropped options get reasons such as "would leave a single token, and every word needs at least 2".
- The key's orange row reads "word lengths · 32 layouts · 5 bits in all"; the green short-word row is gone.
- The summary shows the length bits adding up to 5 "whichever way you got here".
- "Fill randomly" weights options by the layouts they keep, so all 32 layouts are equally likely.
- History entries store `{ value, bits }`. `fmt` rounds, so 1.42 + 1.58 + 2 prints as 5.
- `WORDS` is still injected by the build script but unused by the template.

**Result:** a 3-word phrase is always **66 bits** and a 4-word phrase always **68**, from 5 + 55 + 2 × words.

**Verified with `check_space_game.mjs`:** 32 end states, 15 choice pages, all totals 66 or 68 as expected, no JS errors, and screenshots checked.

**Later, from the user:** cut the 2 or 4 spare bits by shrinking the middle or ending pools.

**"Why 11 tokens?" note on page 1** (asked for by the user): `whyElevenTokens()` is shown as `p.why` under the prompt.
- The user's reasoning: with 10 tokens it is much harder to make normal-sounding words. The 11th token brings 5 bits of its own, plus 1 bit because the words can be split in more ways.
- The numbers are computed in the page:
  - 10 tokens allow 23 layouts, of which a binary index uses 16, so 4 bits.
  - A 10-token phrase holds at most 62 bits, so pools would have to grow, and the tokens get rarer.
  - With 9 tokens: 16 layouts; with 12: 41.
- The blog post should say the same when the game is embedded.

**Next:**
1. Design the token-picking pages with the user, one at a time (open decision 4).
2. Embed the game in the post (open decision 5).

## Session 3, later: game v2 frozen; the Rust phrase_v5 codec matches it

**Frozen:** the game as of the "Why 11 tokens?" note. The user said "that's now frozen".
- Copies: `game/space-game-v2.template.html` and `blog/static/diagrams/space-game-v2.html`, byte-identical to the current files at freeze time.
- Ask before changing the current game's layout pages.

**phrase_v5:** new files only. v1–v4, lenmin and the crate-root `encode_u64` are untouched; `src/lib.rs` gained two lines.
- **Format.** 11 tokens in 3–4 words of 2–5 tokens.
  - The low 5 bits pick one of 32 layouts, in lexicographic order: `LAYOUTS` in `src/phrase_v5.rs`, the same order as the game.
  - Then, word by word, least significant bits first: beginning 7 bits, middles 5 each, ending 5 or 4.
  - The spare bits are spread across endings (user's choice): in 3-word layouts the endings of words 2 and 3 take 4 bits; in 4-word layouts every ending does. Every layout is exactly 64 bits.
- **Tables: context tables, as in v3 (user's choice).** But v3's own tables can't be used.
  - With 2–5-token words they are ambiguous for all 128 beginnings (`ab+ou+s` = `ab+ous`). See `models/check_phrase_v5_ambiguity.py`.
  - So v5 has its own tables. In every context, the 32 middles and 32 endings are prefix-free together, so the decoder finds token boundaries, and with them the layout, from the letters alone.
  - END16 is the first 16 entries of END32.
- **No 1-letter tokens (user's request).** `models/compile_phrase_v5.py` re-tokenizes `training-data/english-lowercase.txt`:
  - The vocabulary uses only 2–6-letter n-grams.
  - Each word gets the best split into beginning, middles and ending (fewest tokens, then highest-ranked pieces).
  - Rows are filled greedily: attested tokens first, then globally frequent ones, keeping prefix-freedom.
  - It writes `models/phrase_v5_model.json`, `models/phrase_v5_report.json` and `src/phrase_v5_data.rs`; `--check` verifies they are reproducible.
  - It also contains the Python reference encoder.
  - Of the corpus's 94,080 words, 62,942 can be split this way. Words under 4 letters can't.
  - Share of each row seen after its context in the corpus: middles 62.5 %, END32 48.1 %, END16 71.4 %.
- **Tests, all passing:**
  - `cargo fmt --check` and `cargo clippy --all-targets --all-features -D warnings` are clean.
  - `cargo test` and `cargo test --all-features`: 34 lib tests plus the cucumber scenarios.
  - The 4 v5 tests:
    - the layouts are every split of 11 tokens, and each is 64 bits;
    - golden values match the Python encoder, and malformed input is rejected;
    - 100k distinct round-trips reach all 32 layouts;
    - every single-bit change in every layout round-trips.
  - `models/test_phrase_v5.py` checks the tables can be regenerated, the invariants and a 20k reference round-trip; v3/v4 Python tests still pass.
- **Comparison.** `cargo run --example phrase_v5_comparison [-- --sample N]`. Over 2,000 values, v4 vs v5:

  | | v4 | v5 |
  |---|---:|---:|
  | Characters per phrase | 28.8 | 27.2 |
  | Real corpus words | 0.3 % | 21.7 % |
  | 3+ consonants in a row | 23.1 % | 19.1 % |
  | Letter 3-grams seen in the corpus | 99.4 % | 98.6 % |
  | Words with no vowel | 0 % | 0.5 % (e.g. `smrs`) |

**Open:**
- Possible table-quality work: rank fallbacks better, or ban words with no vowel.
- README doesn't mention v5 yet.
- The game's toy pools still differ from v5's tables (the game shows sizes, not v5 tokens).
- Nothing is committed.

### v5 table fix: check the join (the user picked only this one)

**Diagnosis of `blness` = `bl` + `ness`:**
- After a beginning, only 27 % of ending-table entries are attested.
- 5,391 attested endings were dropped because a middle blocks them (`in` blocks `ing`, `li` blocks `ling`).
- Fillers were ranked by global count only.
- The user **rejected** "choose middles and endings jointly" and "back off to similar contexts".

**Fix in `compile_phrase_v5.py`:**
- `joins_well()`: every token in a row must make only 3-letter sequences across the join (last 2 letters of the context + first 2 of the token) that occur in at least `MIN_TRIGRAM_WORDS = 5` distinct corpus words.
  - The minimum of 5 matters: with 1, `bitblt` lets `blt` through. With 10 or more, some rows can't fill (`iu`, `ex`).
- Fillers: endings first, then middles.
- In tight contexts (`qu`, `sw`), the rarest attested middles are demoted to fillers until 32 endings fit.
- `validate()` checks the join rule on every row.

**Result, on the same 2,000 values:**

| | v4 | v5 before | v5 now |
|---|---:|---:|---:|
| Words with a 3-letter sequence never in the corpus | 3.8 % | 6.0 % | 0 % |
| …or found in fewer than 5 corpus words | 10.9 % | 11.0 % | 0 % |
| 3+ consonants in a row | 23.1 % | 19.1 % | 14.2 % |
| Words with no vowel | 0 % | 0.5 % | 0.2 % |
| Real corpus words | 0.3 % | 21.7 % | 21.7 % |

- Changed: 1,375 of 2,000 phrases, and the golden values in both tests (for example `0x243f…` is now `dalmse prospicity cindrable`).
- The no-vowel words that remain are a consonant beginning plus a consonant ending: `chts phts shts smst thts whth whts`, about 0.16 % of words.
  - Each join is fine on its own; the problem is the whole word.
  - Possible next rule, not yet proposed to or approved by the user: a word must contain a vowel.
- All checks pass again: fmt, clippy, `cargo test`, `compile --check`, Python tests.

### v5: every word has a vowel (user approved)

**Rule:** after a beginning with no vowel (a, e, i, o, u, y), every middle and ending in its row has a vowel.
- Words have at least 2 tokens, so this guarantees a vowel in every word. It is also the least restrictive rule that does.
- It affects only the 22 vowel-less beginnings (`st ch sp sc sh cr th br gr tr cl fl pl dr fr bl ph sl gl sw wh sm`).

**Enforced in:**
- `compile_phrase_v5.py`: `has_vowel`, and `needs_vowel` in `choose_row`, which is also part of the cache key; `validate()` checks it.
- Rust `validate()`.
- The Rust 100k round-trip test, and the Python reference round-trip.

**Result:**
- All tables still fill; the golden values didn't change.
- 84 of 2,000 sample phrases changed (`whous` → `whable`, `smion` → `smey`).
- Words with no vowel: 0 %. Everything else is unchanged (3+ consonants in a row: 14.1 %).
- All checks pass.

**FROZEN (user, Nov 8): the phrase_v5 codec and tables.** Don't change the format, the tables or the compiler without asking. sha256 at freeze time:
- `src/phrase_v5.rs` 00ae64db…
- `src/phrase_v5_data.rs` f94d9779…
- `models/compile_phrase_v5.py` ee665f05…
- `models/phrase_v5_model.json` c1146f88…

## Game: token pages (in progress, one page at a time)

**User's decisions (clarify, Nov 8):**
- After the layout, the player picks tokens one at a time. Every candidate token is on the page; unavailable ones are muted, with the reason.
- Unavailable tokens are grouped by reason, each group collapsed to a count until opened.
- Each reason has its own muted colour, explained in a colour key.
- The four reasons: "clashes with <token>", "letters don't fit together", "no vowel", "less common here".
- 16-choice ending pages show all 32; the last 16 are greyed out as "not needed: this layout already has its 64 bits".
- The "real v5 tables vs fixed pools" question was skipped twice. I took v5 (the approved reasons only exist there) and said so; the user replied "resume".

**Built: page 1, the first word's beginning** (waiting for the user's review; don't build middle/ending pages yet).
- Replaces the old end-of-layout summary. The layout pages are unchanged (`walk`: 32 end states, 15 pages).
- `build_space_game.py` now takes `BEGIN` from `phrase_v5_model.json`, plus `BEGIN_PAGE`: all 256 beginning candidates with the v5 index, or `clash` (the most common chosen beginning it clashes with), or `less` (after the list filled). Counts are words starting with it among corpus words that split into 2+ letter tokens. 128 pick / 115 clash / 13 less; `BEGIN_LAST` = 127.
- Template: `tokenStep()`, `renderTokenPanel()`, `layoutSummary()`, `REASONS` (clash `#8f7fbf`, less `#bf9a5a`), `state.tokens`; picked tokens show in the slots and turn their gauge segment solid. Undo pops tokens first; Fill randomly picks a uniform beginning.
- After picking: "number k on the list of 128, so it stores the 7 bits 0000000".
- The user's Chromium has one tab with the game, target `3AD9E5CAA6A08F2029623EE54954BD45` (reload it with CDP `Page.reload`). Zola was restarted (see "How to run").
- `check_space_game.mjs` also checks the beginning page (counts, key, pick, undo, random) and saves `05`–`07` screenshots.

**Done (user, Nov 8): the layout pages now use v5's smaller endings.** The user's words: the game "should not say 4 to spare, and it should show that the layout actually chooses reduced tokens".
- Every ending counts as 4 bits: one of the 16 most natural (`END_SMALL`). In a 3-word layout, the first word's ending gets all 32 (5 bits).
- Only the first word's ending depends on the layout. Until the layout is complete it shows 4 bits, and the message adds "5 bits if the phrase ends up with 3 words".
- New helpers: `endingBits`, `bitsAt`, `fullEnding`, `wordBits(lengths, w)` and `describeWord(lengths, w)`. The key's ending row reads "16 or 32 choices, 4 or 5 bits", followed by a note.
- The summary explains which endings have 16 or 32 choices.
- `walk`: all 32 end states are exactly 64 bits; nothing spare, nothing missing. No JS errors.
- The "Why 11 tokens?" note still uses the full 5-bit pools; its point is the best case with 10 tokens.
- The frozen `space-game-v2` copies still show the old 66/68 counts. They weren't updated.

**Built: page 2, the token after the beginning** (user: "next token, same strategy"). Waiting for review.
- **Generic engine.** `tokenSlots()` lists every token slot of the layout. `tokenStep()` returns `beginningPage()` or `followPage(slot, previous)`. `TOKENS_DESIGNED = 2` stops after the second token; raising it enables later pages, which haven't been reviewed yet.
- **`followPage` uses the real v5 rows** injected by the build: `V5_TOKENS`, `V5_MIDDLE`, `V5_END32`, `TRIGRAMS` (5,145 at ≥5 words) and `MIN_TRIGRAM_WORDS`. The page is now about 275 KB.
  - Each candidate's reason is computed in the browser, in the compiler's order: in the row but past 16 (`spare`, "not needed"), `vowel` (only after a vowel-less beginning), `join` (shows the bad 3-letter sequence), `clash` (names the partner and whether it is a middle or an ending), `less`.
- **Colours:** join `#4f9a94`, vowel `#c0708a`, spare `#8c8c8c`.
- `state.tokens` entries are `{id, t, index, size, width}`. After a pick, the message gives its number and its bits (`ad` = number 18 of 32 = `10010`).
- **The check matches the Python counts exactly:**
  - middle after `re`: 32 / join 20 / clash 137 / less 323;
  - 32-ending after `re`: 32 / 11 / 90 / 123;
  - 16-ending after `bl`: 16 / spare 16 / vowel 32 / join 112 / clash 78 / less 2.
  - No JS errors; random fill goes through both pages.
- The note says lists are "the ones that follow X in English words, most common first, topped up with the most common overall". Honest: after `bl`, only 2 endings come from real corpus words.

**Built: every word, start to finish** (user: "let's do the next word, go over the words"). Waiting for review.
- `TOKENS_DESIGNED` is gone: pages run through all 11 tokens.
- After each word's ending, the message says "The first word is done: reable".
- Beginning pages of later words get a short note ("The same 128 as for the first word…") instead of the long one.
- **End page.** `finalSummary()` shows:
  - the phrase;
  - the layout number among the 32 (`LAYOUT_LIST`, tuple order as in v5), the lowest 5 bits;
  - each token's number in binary, left to right;
  - the 64-bit number in hex and decimal (`phraseNumber()`, BigInt).
- **Check:** 200 complete random phrases (driving `step()` directly). All are 64 bits, cover all 32 layouts, and `compile_phrase_v5.encode(value) == phrase` for all 200. Results in `$TMPDIR/space-game-check/phrases.json`.
  - Screenshots: `12-word2-beginning.png`, `13-final.png`.
- **Possible polish, not yet requested:** the end message is one long paragraph and might read better as a small table of the bits.

## Design in progress (not implemented)

**Agreed pools:** 128 beginnings (7 bits), 32 endings (5 bits), 32 short words (5 bits). Middles are 32 (5 bits); that was proposed for 11 tokens, but the user hasn't confirmed it.

**Layouts:** 11 tokens, up to 4 words, built words of 2–5 tokens, at most 2 short words ("1"), short word never last and never next to another. This gives **72 layouts**, including the user's `1+4+1+5`. With 64 of them, the layout is worth 6 bits.

- **No short word (32):**
  - 3 words: `2+4+5 2+5+4 3+3+5 3+4+4 3+5+3 4+2+5 4+3+4 4+4+3 4+5+2 5+2+4 5+3+3 5+4+2`
  - 4 words: `2+2+2+5 2+2+3+4 2+2+4+3 2+2+5+2 2+3+2+4 2+3+3+3 2+3+4+2 2+4+2+3 2+4+3+2 2+5+2+2 3+2+2+4 3+2+3+3 3+2+4+2 3+3+2+3 3+3+3+2 3+4+2+2 4+2+2+3 4+2+3+2 4+3+2+2 5+2+2+2`
- **One short word (38):**
  - 3 words: `1+5+5 5+1+5`
  - 4 words: `1+2+3+5 1+2+4+4 1+2+5+3 1+3+2+5 1+3+3+4 1+3+4+3 1+3+5+2 1+4+2+4 1+4+3+3 1+4+4+2 1+5+2+3 1+5+3+2 2+1+3+5 2+1+4+4 2+1+5+3 3+1+2+5 3+1+3+4 3+1+4+3 3+1+5+2 4+1+2+4 4+1+3+3 4+1+4+2 5+1+2+3 5+1+3+2 2+3+1+5 2+4+1+4 2+5+1+3 3+2+1+5 3+3+1+4 3+4+1+3 3+5+1+2 4+2+1+4 4+3+1+3 4+4+1+2 5+2+1+3 5+3+1+2`
- **Two short words (2):** `1+4+1+5 1+5+1+4`

**Token bits.** A built word of *n* tokens holds 7 + 5 + 5(*n*−2) = 5*n* + 2 bits with 32 middles. So 11 tokens hold 55 + 2 × (number of built words) bits. Layout bits push this to 64 or more.

| Built words | Layouts | Token bits | + 6-bit layout | + 5-bit layout |
|---|---:|---:|---:|---:|
| 2 | 4 | 59 | 65 | **64, exact** |
| 3 | 48 | 61 | 67 | 66 |
| 4 | 20 | **63, the most** | 69 | 68 |

**The user's last question, not yet answered in chat:** "3 built words, with or without a short word — how many combinations?" The answer is **48**: 12 three-word layouts without a short word and 36 four-word layouts with one. All hold 61 token bits with these pools.
- If the game is limited to those 48 layouts, 32 of them give a 5-bit layout (66 bits, 2 spare), or 8 give exactly 64.
- Other pool choices for those 48 layouts, checked:
  - 64 middles: 65 or 66 token bits;
  - 64 beginnings, 16 endings or 16 middles: 56–58 token bits, which needs 6–8 layout bits that 48 layouts can't give.

**Earlier rejected options:**
- **10 tokens:** at most 2–4 words with one short word gives 57 layouts. The 5-bit set would be the 34 one-short-word layouts minus two. The user said "that's not enough".
- **More than 4 words:** reads like word salad.

## Open decisions for the user

1. **Which layouts:** all 72 (6 bits), only the 48 with three built words, or another subset? Which ones get dropped to reach a power of two?
2. **Is the layout one pick or several pages?** For example word count, then short-word position, then lengths. The confirmed step 1 ("first word length") may need to be reconciled with this.
3. **Middles at 32:** confirm.
4. **Token-picking pages:** how the player picks beginnings, middles, endings and short words; whether to show real tokens and a final phrase.
5. **Embedding:** whether and how the game goes into `bits-in-the-spaces.md` (iframe or a link to `/diagrams/space-game.html`), and whether the post text should change to the 11-token story.

## Next steps

1. Get answers to 1–3, then update the pools in `game/build_space_game.py` (`BEGIN_COUNT = 128`, 32 endings, 32 middles) and the layout logic in `nextStep()` in the template.
2. Design and build the token-picking pages, one at a time, with the user.
3. Embed the game in the post; keep both posts drafts.

## Other state worth knowing

- **This repo** has a lot of uncommitted, staged and untracked work: the phrase v2–v4, dyn and lenmin encoders, and `models/overnight/`. Never reset or clean it. `game/` and this file are new and untracked.
- **The real encoder:** the lenmin encoder (`src/phrase_lenmin.rs`) was the best result; see `models/OVERNIGHT_REPORT.md` and `models/overnight/results/report.html`. The 0.11 release post assumes it ships as `encode_u64`/`decode_u64` with a reversible mix. That's "fake before we make": post first, release later.
- `gh` is not authenticated, and `git fetch` through the proxy fails. Read GitHub and crates.io state with curl and the public APIs.
