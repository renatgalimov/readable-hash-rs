# Experimental phrase model compiler

Run `python models/compile_phrase.py` to regenerate `phrase_model.json` and
`phrase_report.json` and `src/phrase_v2_data.rs`; run with `--check` to verify exact reproducibility.
These are separate from, and do not change, the reversible v1 model. Run
`python -m unittest discover -s models -p 'test_*.py'` for Python tests.

## Model interface

`phrase_model.json` contains `tokens` (1024 position-marked source strings),
`contexts` (IDs 0..255 followed by 512..1023), `begin` (128 token IDs),
`middle16` and `middle8` (768 rows, 16 and 8 IDs respectively), and
`end128` (768 rows of 128 IDs). Rows use the corresponding entry of `contexts`;
thus a beginning ID indexes directly and a middle ID indexes at ID minus 256.
Strip one leading `^` and one trailing `$` when emitting token text. Rows are
ordered lexicographically by emitted spelling, not by frequency; row order is
part of the format. The 8-choice row is independently optimized and is not
necessarily a prefix of the 16-choice row. Beginning IDs can include a middle
ID if the training tokenizer used it as a fallback.

Use B/M16/M16/E for word one and B/M16/M8/E for words two and three, resetting
context at each word. Each row is independently validated for exact size,
lowercase distinct prefix-free spellings and valid IDs; every beginning and
middle has a complete row. Consequently, decoding a fixed four-token word is
unique by induction, and all paths terminate. Cardinalities provide exactly
22+21+21 bits, so a fixed bit order yields a bijection over u64 and phrases;
two literal spaces delimit the three words. The Rust `phrase_v2::encode_u64`
and `phrase_v2::decode_u64` use these frozen tables and consume bits least
significant first, B/M/M/E from left to right. They do not change the v1 API.

## Selection and report

Counts are reconstructed and verified against the checked-in corpus model.
For each row, trie dynamic programming chooses the required cardinality,
maximizing sum of observed local counts, then the sum of global counts for
selected unobserved tokens, then the lexicographically smallest token tuple.
This jointly optimizes local retention and global fallback under the prefix
constraint: it does not greedily select locals that make the row infeasible.
Every row is generated, including unreachable ones, so all beginnings have
full complete paths. Beginning selection maximizes the total number of distinct
selected observed B->M->M->E paths (using the M16 tables) and then beginning
frequency. These are viable choices in prefix-free selected rows, not raw ID
counts or corpus word counts. This heuristic is not a global optimization of
all paths or word readability; unobserved transitions are still viable via
fallback. Ties are lexical.

`phrase_report.json` lists omitted observed token strings per context ID for
each table, plus omitted beginnings, row-local slot counts and exact reachable
path-weighted statistics. Coverage counts are per position for uniform choices,
not corpus-frequency-weighted. Length extrema are exact dynamic-programming
bounds over all paths; the mean is under independent uniformly distributed
choice indices, not natural-language or corpus probabilities. Add the two
spaces to letter counts for total phrase characters.

For this frozen model, exact bounds are 15 to 48 letters plus two spaces;
the uniform-u64 mean is 28.37257194519043 letters. Uniform reachable-path
ending locality is 23.9754% for word one and 23.9718% for words two and three;
the rest are fallback. First-middle locality is 100%, and second-middle locality
is 99.2950% and 99.9756%, respectively. These are model transition coverage,
not linguistic quality measurements. Rows and omissions include unreachable
contexts; consult the JSON report for individual omissions and exact counts.
