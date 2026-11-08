# Overnight report: dyn v1 (Part A) and length-minimized lenmin v1 (Part B)

Document map: Part A results (dyn v1, written by the first run, re-verified in the continuation) are directly below;
Part B (lenmin v1, the new primary objective) is at the end under "PART B". HTML: models/overnight/results/report.html
(Part B first, Part A body after it). Machine-readable: models/overnight/results/lenmin_summary.json (Part B),
models/overnight/results/summary.json (Part A). Nothing was committed, pushed or merged; existing staged/unstaged v1-v4 work is untouched.

## Part A results (continuation re-verification)

- Full suite re-run by the continuation agent (log: models/overnight/results/test_status.txt): cargo fmt --check ok;
  cargo test default 30 lib tests + 19 cucumber scenarios (15 passed, 4 feature-gated shake256 skipped) ok;
  cargo test --all-features 30 lib tests + 19/19 scenarios ok; cargo clippy --all-targets --all-features -D warnings exit 0;
  Python unittest scripts (test_phrase_model, test_phrase_v3, test_phrase_v4, test_reversible_tables, overnight/test_dyn, overnight/test_lenmin) OK.
- Read-only review of src/phrase_dyn.rs and src/bounded_grammar.rs finished by self-review (no @code-review bot available; disclosed):
  parser rejects empty/uppercase/non-alphabetic tokens, prefix conflicts, forward-only targets (acyclic, terminating), wrong state count and
  insufficient capacity; all counts are checked u128; decode rejects ranks >= 2^64, non-canonical spacing, case and trailing text. No defect found
  that needed a code change. Remaining caveats are design limits, not bugs: dyn v1 words are base-W digits, so 2^64 / capacity of the grammar is unused
  (24.7 percent utilisation for the selected model) and low ranks are visibly low-entropy (see mix v1 below).
- Part A artifacts are unchanged: src/phrase_dyn.rs, src/dyn_models/*.txt, examples/phrase_dyn_comparison.rs, models/overnight/{fetch_sample,extract_counts,compile_dyn,sweep,report,test_dyn}.py. report.py now writes results/report_partA.html; report_lenmin.py composes the final report.html.

--- Part A body (as written by the first run) ---

Status: COMPLETED with working, tested artifacts. dyn v1 is experimental. It does not replace
v1 (encode_u64) or phrase v2/v3/v4; all of those APIs and files are unchanged apart from one
new `pub mod phrase_dyn;` line in src/lib.rs. Nothing was committed or pushed.

## What was built

- src/phrase_dyn.rs: a generic rank/unrank codec over a bounded, acyclic, prefix-free word
  automaton (`Model::parse`, `encode`, `decode`, `rank_word`, `unrank_word`), plus `mix`/`unmix`
  ("mix v1", the splitmix64 finalizer and its exact inverse). `mix` is an optional, separately
  versioned spreading permutation. It is not encryption.
- src/dyn_models/{en-unique,en-fineweb,tr-fineweb}.txt: three frozen models in the
  `dynphrase v1` text format, embedded with include_str! (each about 120-140 KB).
- models/overnight/: fetch_sample.py (HTTP Range parquet fetch with a hard byte cap),
  extract_counts.py, compile_dyn.py (grammar compiler, Python reference codec, exact metrics),
  sweep.py, report.py (independent Python parser, Rust/Python cross-check, proxy metrics, HTML),
  test_dyn.py.
- examples/phrase_dyn_comparison.rs: 63 fixed inputs compared across v4 and dyn, every
  encoding decoded and asserted; `--sample N` prints a deterministic LCG sample.

## Codec design (as implemented)

- Word grammar: B (M|E){0..3} E. Each word has 2 to 5 tokens and ends on an explicit end token.
  State = (slot, previous token). Each next state has a strictly higher index, so the grammar
  is acyclic and always terminates. Choices within a state are prefix-free over the emitted text,
  checked by the compiler, by the Rust parser and by the Python parser. So a word parses
  deterministically and different paths cannot produce the same text.
- Choice set per state: tokens greedily taken in quality order (local transition weight, then
  global weight, then text). A token is accepted only if it does not create a prefix conflict
  and is attested after this context in at least 2 distinct training word types. The set is
  capped at `cap`. Backoff (global-frequency tokens of the same class) is added only if fewer
  than 2 choices exist. So weak contexts get small fanout. No tokens come from outside the
  learned vocabulary, and there is no filler to reach capacity.
- Ranking: W = number of complete words, computed by a completion-count DP with checked u128 in
  Rust and big integers in Python. Each choice owns a contiguous interval of ranks whose size is
  its subtree count. The phrase is 3 words: the u64 written in base W, first word most
  significant. Decoding adds the offsets back and rejects any rank >= 2^64. There is no modulo
  reduction, no weighting collisions and no registry. All 64 bits are preserved because the
  mapping is a bijection onto ranks [0, 2^64). Bits are not claimed per node: the information
  is preserved globally through the integer intervals.

## Key measured findings (exact unless marked as a sample)

1. Capacity is the binding constraint. With words of at most 4 tokens, no cap (16-256) reaches
   2^64 with 3 words, for any corpus: the best was en-unique, 2^62.9. With at most 5 tokens it
   is feasible from cap 32 (en-unique, tr) or cap 64 (en-fineweb). Requiring stronger support
   (>= 4 or >= 8 word types per transition) makes it infeasible or nearly so (see the sweep in
   results/summary.json). So 3 natural words with 64 bits is at the edge of what attested bigram
   paths give: about 21.3 bits per word.
2. Length and distribution bias is inherent. A uniform u64 selects codewords uniformly, so the
   word-length distribution equals the codebook composition: about 92-95% of words are
   5-token words (exact, from tokens_hist). Interval ranking cannot favour short words without
   removing long words from the codebook.
3. Unused ranks: capacity/2^64 is 4.0x (en-unique cap32), 2.05x (en-fineweb cap64) and 1.55x (tr
   cap32). All unused ranks fall in the first word's high-rank tail, so the first word only
   reaches the best-quality ~25% / 49% / 65% of W. The second and third words reach all of W
   (exact multiplicities in word_weights). The first word is therefore biased toward
   higher-ranked, better-quality choices; this is quantified, not hidden.
4. Selection rule, fixed before looking at examples: lowest held-out not-attested transition
   rate among feasible 3-word caps, smaller cap on ties. This chose en-unique cap32,
   en-fineweb cap64 and tr cap32.

Selected models:

  model        W         log2 cap  mean letters (exact)  heldout-unattested trans.  fallback trans.
  en-unique    4208375   66.01     29.90                 41.2%                      0.0015%
  en-fineweb   3356972   65.04     30.99                 24.5%                      0.038%
  tr-fineweb   3055350   64.63     28.78                 16.9%                      0.0097%
  (v4 for reference: mean 26.87 letters, from PHRASE_V4_COMPARISON.md)

"Transition rates" average over all W word paths equally. Words 2 and 3 follow this to within
2^-40 under uniform u64; word 1 is truncated as explained in finding 3. No retries exist in a
rank codec. "Fallback" is the share of transitions that use backoff rows.

Proxy metrics over 20,000 LCG inputs (seed 99; a sample, not exact). Spelling is scored by a
char-trigram model trained on the held-out split of the FineWeb sample in the same language
(lower = more natural; real top-20k train words score en 3.47 and tr 3.19 bits/char):

  arm                letters  char3 bits/char  real-word rate  repeated word  risk-substring rate
  v4                 26.87    4.406            0.06%           0              1.06%
  dyn en-unique      29.91    4.583            0.02%           0              0.85%
  dyn en-fineweb     30.98    4.127            0.08%           0              1.20%
  dyn tr-fineweb     28.78    4.478            0.05%           0              1.55% (mostly "sik" false positives)
  dyn en-unique+mix  29.90    4.592            0.02%           0              0.97%

Fairness caveats: (a) en-unique vs v4 is the fair comparison: same 94,080-word list and same v3
vocabulary. There dyn is about 3 letters longer and slightly worse on the spelling proxy, so on
this data dyn v1 does NOT beat v4. (b) en-fineweb scores best, but its training corpus and the
judge's held-out split come from the same distribution. It also uses 47,864 filtered types
instead of 94,080, so part of that gain is corpus matching. (c) The Turkish numbers are not
comparable to the English ones. No human or native-speaker validation was done. I inspected the
examples myself: they are pseudo-words of varying awkwardness ("revers revers revers" at 0,
"budgfgp", "leverbcale"). Substring matches on offensive terms occur in about 1% of phrases for
every arm, including v4; no filter is applied.

## Examples (input | v4 | dyn en-unique | dyn en-fineweb | dyn tr-fineweb | en-unique with mix v1)

All 63 rows are in models/overnight/results/examples.csv and examples.json. Every cell was
decoded and checked in Rust, and the dyn cells were re-encoded by the independent Python parser
with 0 mismatches over 63 + 5,000 rows. The DefaultHasher rows use
DefaultHasher::new()/write(bytes)/finish(), which is not stable across Rust versions. The "hello"
row equals 16350172494705860510, the same as earlier runs. The unpermuted columns are the
baseline; the mix column is shown separately.

  fixed:0x0                    | abandaia abandaal abandaia | revers revers revers | ofference ofference ofference | hastalık hastalık hastalık | revers revers revers
  fixed:0x1                    | adaiaca abandaal abandaia | revers revers revert | ofference ofference offerenting | hastalık hastalık hastalım | unmorapex beaufficative panowkle
  fixed:0x2                    | alarbable abandaal abandaia | revers revers reveryths | ofference ofference offerential | hastalık hastalık hastalığı | seignopling hornutinan secelocue
  fixed:0x3                    | anacaia abandaal abandaia | revers revers reverythy | ofference ofference offerention | hastalık hastalık hastalıdır | reapodils procrucleon tabumorrence
  fixed:0x2a                   | exactaca abandaal abandaia | revers revers reverymotor | ofference ofference officulus | hastalık hastalık hastalıglar | beadbarious haydovied temposopping
  fixed:0xff                   | wobuba abandaal abandaia | revers revers reverywals | ofference ofference offended | hastalık hastalık hastanin | eastasbut iriventices reviolbes
  fixed:0x100                  | abbabiage abandaal abandaia | revers revers reverygon | ofference ofference offenda | hastalık hastalık hastance | paciencement sofreola telegravius
  fixed:0x3e8                  | shaemada abandaal abandaia | revers revers reverlagow | ofference ofference offolutting | hastalık hastalık hastroudi | masconple detaxix tactyloit
  fixed:0xffff                 | woundhoan abandaal abandaia | revers revers remadilloes | ofference ofference olecapage | hastalık hastalık hapudip | massomime tangfirmes bestinimois
  fixed:0x75bcd15              | certiwking couchaberal abandaia | revers reverymous sawbariding | ofference officuld baffload | hastalık hastalıgre yeyişittle | pawdmotive requisephus rodovados
  fixed:0xffffffff             | woundzz wofuciable abandaia | revers reverlazy aeobrotus | ofference offlous hordomodate | hastalık hastrios sikiyasel | bertwarra sophaefed procratified
  fixed:0x100000000            | abandaia abduba abandaia | revers reverlazy aeobrota | ofference offlous hordomodium | hastalık hastrios sikiyasek | sepakbos bawcohos talphistian
  fixed:0x7fffffffffffffff     | woundzz woundruz woundzine | deathlesomes farcissolton poispoones | procerylink analgapipe boattabour | safteresan sezülislar desteriyası | untizle bactroadian cathorcium
  fixed:0x8000000000000000     | abandaia abandaal abandaims | deathlesomes farcissolton poispooner | procerylink analgapipe boattabox | safteresan sezülislar desteriyal | effeet bourkneve disobrovies
  fixed:0xfffffffffffffffe     | wizzz woundruz woundzy | panibasible iodlipoise meanjoto | leverbcale icemilaid totalitamins | tativeyması disfusal bilsinekleyeyle | seventicipps remadoffish bastiffeep
  fixed:0xffffffffffffffff     | woundzz woundruz woundzy | panibasible iodlipoise meanjotism | leverbcale icemilaid totalitaminal | tativeyması disfusal bilsineklemeye | mainkwing unfacipium sixpectly
  fixed:0x243f6a8885a308d3     | orierling chairasseth steinctare | epidicement hamaditating hauggirley | thravacum secelemmit lastcoverge | içişöropla olanıyısty insiyajlar | palacramen ramissineve matrifacity
  fixed:0xdeadbeefcafebabe     | jerredy favoureth hereivation | serarimpion rodolwey solebrosius | lockbrator fondlodies facerysal | günecihra üniliksiz delazben | debivoirless distraribey ediculluit
  fixed:0x5555555555555555     | overflinless overflanny exonemont | unworleman sootiduition depopus | epilebration ombrangel daffeutening | dakibiplu ürobiyada saçrafken | mawbunax tearchion cooposcund
  fixed:0xaaaaaaaaaaaaaaaa     | exonemory exonetces overflinny | macbasits rosadstow settucinate | wolgression ancertcoin paperbation | helaçram daneciktur tabihset | bedhovig gamefartz lauggio
  fixed:0xf0f0f0f0f0f0f0f      | broughings interrobous ricawder | requipagon beadilward raffairmer | anglypaid digemodas necrepended | hayişterip kastehayeyi dinlensfu | patrimonix hazzires maznemis
  fixed:0xf0f0f0f0f0f0f0f0     | tablemote ladwed cravicius | pantwopei holdburda sassposie | derivejs fibertarps besipabins | medluncy telasefs medropliği | serendaffey ithcocium sabindhood
  fixed:0xff00ff00ff00ff       | wobundy annizan revoceable | remoraptis tercotnois passuncier | owleaded lilawyed taxvicting | hayabebiye buttükbaz taçtuldiler | depedigit sibholded requitthen
  fixed:0xff00ff00ff00ff00     | abutifal voglafs creaguez | patersbae sojodotum unhemekes | leathtable suckorcity bassifinist | tabarekenin hegecibu bezirica | defabumini litiriggie sombirfist
  fixed:0x101010101010101      | adanslce archiater croacharial | remoraging lithnoplant solukewed | owlegial proficiopes leximum | hayabedesi dayabesty badeppma | matermekes lambuclily soladidating
  fixed:0x8000000000000001     | adaiaca abandaal abandaims | deathlesomes farcissolton poispooney | procerylink analgapipe boattabow | safteresan sezülislar desteriyacak | renavivator regamorta iodosime
  fixed:0xffffffff0000         | abandoay woundruz creagansan | reverythful gascillots ililoid | offerestern condefixity nestmarily | hastalıyden tetvekiye birinemenizle | betovadox dishoffrif evoiduary
  fixed:0x123456789abcdef0     | taunellus sidestire blakedoes | remeloquire lightcaype safeeblour | anceset fizmothen aligibly | ilâdefli olayletrisi tadıgmear | betthracon bersuivate raregamius
  pow2:56                      | abandaia abandaal abandaua | remoravenire potakebon unlagicive | owlemming eeristiviation couldlifies | hayabestinin ayıysarettir sadıçrayı | depezzied matrifacive soapodbie
  lcg:0                        | briddleated eshyton sitteila | remosage cowdstable soludoffle | optogginal wieloactive toennawable | hakfram ginzistır olamımıs | devarokes proclussia tenibursch
  lcg:1                        | liddenily carrowy altailey | berndealie idolwart sillimellah | pronoyote beaughthood annautdon | sattükreye hakrap kepissebilir | pantlevious benegadium bouccohoon
  lcg:2                        | tawhtx cortemits unguerras | evaromoire ejustada farcopotism | yadowdog panomacol egaciary | ülpahd giveyhli helloslim | majibute talsampter lathiopog
  defaulthasher:hello          | crazader filianm subtencium | secondnow unpredulk baywatcham | locomony tenodewart genifinance | gübcriz sirkedifs talillektin | matrifies tabourvium unbursmily
  defaulthasher:example        | scalwash riccently notewart | secrobosure tamadiceful proclotlime | bundfinai notichoundry dawledia | malörizlerde hematofra alkneğinde | earhewy besembacis coffrivain
  defaulthasher:readable hash  | rejurians riolubd maypias | earctic gascillefly babjodized | wiseeigners whosphother fabridimized | üforlantı gibiyahı invatur | reascessie seconceloid unlomedits
  defaulthasher:hello world    | blastolers cressenaire jemmagne | massborum bersmise hopendiwow | fifraigate rediregic bedrotaps | hegelenimlerde çötilmeli hankestir | bestroppop unboldcala galopolitating
  defaulthasher:readable-hash-rs | naphurred mumbricion pawritis | maxxpeth teledowdly tapenewaite | frenagrain sinodemire honchbos | hemaşayın solizönü tabeziraz | rebecophia depenee camplacel

Low and structured inputs repeat the rank-0 word ("revers", "ofference", "hastalık"). mix v1
spreads these values but does not prevent repetition in general and gives no security.

## Corpus provenance (manifest: /home/agent/corpora/readable-hash-overnight/MANIFEST.json)

- en: HuggingFaceFW/fineweb @ 9bb295ddab0e05d785b879661af7260fed5140fc,
  sample/10BT/000_00000.parquet (train data). ODC-By 1.0, also subject to the CommonCrawl Terms
  of Use. HTTP Range reads of the footer plus 32 row groups: 67.7 MB transferred out of a 2.15 GB
  shard. Retained 31,964 documents, 99.998 MB clean UTF-8, as a 41.2 MB gzip (sha256 in the
  manifest).
- tr: HuggingFaceFW/fineweb-2 @ af9c13333eb981300149d5ca60a8e9d659b276b9,
  data/tur_Latn/train/000_00000.parquet, same license. 56.1 MB transferred; 20,775 documents,
  99.986 MB of text, 37.7 MB gzip.
- The transfer cap (400 MB) was enforced on bytes actually received. robots.txt allows access.
  No raw text is in git; only aggregated lowercase word counts are produced, and those also stay
  outside git.
- Extraction (extract_counts v1): NFC normalization; Turkish casing (I->ı, İ->i); per-language
  alphabet whitelist (tr includes çğıöşü âîû); length 2-24; triple repeated letters rejected;
  lines repeated in >= 5 documents dropped as boilerplate; doc_freq >= 3; words capitalized in
  >= 90% of occurrences dropped (likely names or PII). Train/held-out split by sha256(id)
  (about 10%), made before any counting.
  Occurrence counts and document frequency are both kept; "unique" means type-level weight 1.
  Known artifact: apostrophe suffixes split off in Turkish ("Ankara'nın" -> "nın").
- Disk: corpus directory 77 MB; scratch pyarrow venv 169 MB (removable); about 93 GB free. No
  HuggingFace cache was used. The corpus was not scaled past 100 MB per language: the metrics
  showed capacity, not data volume, as the binding limit.

## Tests (models/overnight/results/test_status.txt, re-run after the final code)

- cargo fmt --check OK. cargo test (default): 24 lib tests pass; cucumber 15 passed and 4
  skipped (shake256 feature). cargo test --all-features: 24 lib tests and all 19 cucumber
  scenarios pass. clippy --all-targets --all-features: no warnings.
- Rust phrase_dyn tests: exhaustive reduced-model bijection with an independent enumeration;
  prefix and suffix rejection; parser counts; invalid models (header, prefix conflict, cycle,
  empty, uppercase, count, out-of-range target) rejected; insufficient capacity rejected; the
  edge values 0, 1, 2, 42, 1000, 123456789, 2^63-1, 2^63, 2^64-2 and max for each real model,
  with malformed inputs (leading or trailing space, double space, tab, uppercase, extra word,
  joined words, empty, every truncation) and the out-of-range top phrase rejected; 100k
  deterministic roundtrips with uniqueness per model; mix/unmix inverse on 100k values; a
  Turkish model with Turkish letters reachable, NFD input rejected and ı/i not folded.
- Python: test_phrase_model, test_phrase_v3, test_phrase_v4, test_reversible_tables and
  overnight/test_dyn all OK. test_dyn covers the reduced exhaustive case, the exact metric mass
  (2^64), Turkish casing, frozen-model structure and roundtrip, and confirms that all 3 frozen
  models are regenerated byte-for-byte from the corpus counts. test_obfuscation.py and
  test_tokenizer.py are manual CLI tools, not tests, and were not run.
- Review: no @code-review tool exists in this session. One bounded reviewer subagent was started
  but was interrupted by the runtime before it reported anything, so the only review is my own
  self-review. Note also that `cargo fmt --all` reformatted the pre-existing untracked
  src/bounded_grammar.rs (formatting only; its logic was not changed).

## Performance

The Rust run did 200k encode+decode in about 0.20-0.22 s per model (release build). Compiling
all sweep arms took a few seconds per arm, with a Python max RSS of a few hundred MB (see
summary.json).

## Recommendation and next design

- Keep v4 as the baseline. On the fair same-corpus comparison, dyn v1 is not more readable and is
  longer. What dyn v1 adds is a proven exact, variable-radix, context-dependent codec engine that
  separates grammar quality from bit packing.
- Next: (1) Train on running-text frequencies with a vocabulary built from that corpus (the v3
  vocabulary was trained on unique words). (2) Add word-level, not only bigram, attestation:
  for example, put real frequent words as whole codewords into the codebook alongside generated
  ones, because real-word rates are currently about 0.05%. (3) 4 shorter words versus 3 longer
  ones: the 4-word arm with at most 4 tokens is feasible at cap 32 (2^72.4) and should go to a
  human readability test. (4) The multilingual selector idea (a language-identifying first
  word) fits this engine as a first-word state with disjoint per-language subgrammars, but it was
  not implemented because the idea is not finalized.
- Rejected or not done: raw 256-way fanout (not distinct, pronounceable choices); a lossy modulo
  or probabilistic suffix; expanding with nonsense to reach capacity; adaptive power-of-two
  branching. Power-of-two branching was not benchmarked: it needs a bit-stream termination
  rule and wastes the fractional capacity this design keeps.

## Reproduce

  V=~/.hermes/profiles/programmer/cache/scratch/rhvenv/bin/python   # venv with pyarrow
  $V models/overnight/fetch_sample.py en; $V models/overnight/fetch_sample.py tr
  python3 models/overnight/extract_counts.py en; python3 models/overnight/extract_counts.py tr
  python3 models/overnight/sweep.py            # writes results/sweep.json and src/dyn_models/*.txt
  cargo run --release --example phrase_dyn_comparison > models/overnight/results/examples.csv
  cargo run --release --example phrase_dyn_comparison -- --sample 20000 > sample.tsv
  python3 models/overnight/report.py sample.tsv  # summary.json, proxy_metrics.csv, report.html
  python3 models/overnight/test_dyn.py; cargo test; cargo test --all-features

Artifacts: models/overnight/results/{summary.json, sweep.json, examples.csv, examples.json,
proxy_metrics.csv, report.html, test_status.txt, timing.log, sweep.log}.


# PART B: length-minimized phrases (lenmin v1)

## Objective and result

Minimize phrase length (letters + spaces) while keeping all 64 bits: an exact, injective, reversible u64 <-> phrase mapping.

Headline over uniform u64 (3 codecs, same u64 space):

  codec                      words        bits  mean len  max len  how measured
  v4 (existing)              3            64    28.87     40       sampled, 200k LCG values
  dyn v1 en-unique (Part A)  3            64    31.90     45       mean exact, max sampled 200k
  lenmin v1 (selected)       2-4 (3.14)   64    23.60     24       exact (DP over all 2^64 values)

Selected: 18 percent shorter mean and 40 percent lower max than v4; 26 percent shorter mean than dyn v1.
Exact length distribution of the selected model (share of u64 values): 24: 66.5 percent, 23: 28.1 percent, 22: 4.5 percent,
21: 0.70 percent, 20: 0.10 percent, shorter lengths below 0.02 percent (full table in lenmin_summary.json and report.html). Median 24, p99 24.
Word count: 3 words 86 percent, 4 words 14 percent, 2 words 0.015 percent (sampled, 20k).

## Design

- Grammar (per word): acyclic prefix-free automaton from the v3 1024-token English vocabulary and the 94,080-word unique list. Start row: curated real
  one-token words first (greedy, prefix-free), then up to 256 beginning tokens by quality. Later rows are per (slot, previous token) context: corpus-supported
  continuation tokens by quality, capped (64 in the selected arm), backoff only below 2 choices (fallback share 1e-5 for the selected arm). Words have 1-5
  tokens. "Ending-constrained": a multi-token word must end on an end token. The selected arm uses it.
- Phrase: k words (k in 2..4) joined by single spaces. Order: total length (letters + spaces), then word count, then first word length, first word rank,
  second word length, ... The u64 is the position in that order; positions >= 2^64 are invalid (decode returns None). This is exactly "the 2^64 shortest valid phrases get 0..2^64-1", so it minimizes both mean and max length for the grammar. Grammar capacity is 2^101.5, so only a 2^-37.5 slice (the shortest) is reachable.
- Implementation: DP counts N[state][remaining letters] (words with exactly that many letters), word-length counts, k-word sequence counts, per-length class
  totals. encode = choose length class by cumulative counts, then word lengths, then unrank each word by completion counts at fixed remaining length.
  decode = parse each word greedily (prefix-free), rank it, sum interval offsets. Checked u128 everywhere. No modulo, no collisions, no padding.
- Code: src/phrase_lenmin.rs (Model::parse/encode/decode, models::EN_UNIQUE from src/lenmin_models/en-unique.txt, re-exports mix/unmix), reference and builder in Python:
  models/overnight/{lenmin.py,compile_lenmin.py,sweep_lenmin.py,architect_check.py,test_lenmin.py,crosscheck_lenmin.py,report_lenmin.py}. New explicit version string
  "lenmin v1"; v1-v4, dyn v1 and bounded_grammar are unchanged (one `pub mod phrase_lenmin;` line added to src/lib.rs).
- Optional pre-mix: lenmin::mix / unmix (splitmix64 finalizer, invertible, same as dyn "mix v1"). Raw small values give the shortest phrases ("to to" for 0,
  "to of" for 1, "of up" for 42), which is by design for length-major order. Mixed examples are shown next to raw ones. This is not encryption, adds no security, and does not remove repetition.

## Architect analysis, checked numerically (models/overnight/architect_check.py)

Idealised grammar B=128, C=64, exactly 3 words, 1-4 tokens/word, free spaces, length measured in tokens: single 10-token layout = 63.0 bits, six layouts of 10 tokens
= 65.58 bits, length-major mean 9.92 tokens and max 10, versus 11 tokens for the best fixed layout (3+4+4, 69 bits) and 12 for 4+4+4 (75 bits). Confirmed. With letters instead of
tokens the effect is the same: free word lengths let spaces and layouts carry entropy. In the real model the bigger effects are the much larger continuation pools (64
per context, 256 beginnings, up to 5 tokens) and 2-4 free word counts.

## Sweep and Pareto (models/overnight/sweep_lenmin.py, results/lenmin_sweep.json, 376 arms)

Axes: words 2/3/4/free(2-4); max tokens per word 3/4/5/6; begin cap 128/256; continuation cap 16/32/64; ending free vs constrained; curated one-token words on/off; sources English
unique-word list, English FineWeb occurrence weights, Turkish FineWeb2 (native Unicode; curated English list not used). 214 arms reach 2^64 capacity. 162 are rejected
for insufficient capacity (for example every 2-word arm up to 6 tokens, most 3-token and many 4-token arms; nothing padded to fit). Proxies are sampled from 5,000 seeded uniform u64 per arm.
Key rows (len = letters + spaces; unatt = share of transitions never seen in held-out text; real = share of generated words that are real corpus words; nonend = words ending on a non-ending token):

  arm                                                  mean   max  log2cap  unatt  real   nonend  fallback
  en-unique b256 c64 t5 constrained cur w2-4 (SELECTED) 23.60  24   101.5    0.46   0.060  0.00    0.00000
  en-unique b256 c64 t5 constrained cur w3              23.83  25    76.1    0.47   0.023  0.00    0.00002
  en-unique b256 c64 t4 constrained cur w4              23.92  25    84.3    0.40   0.149  0.00    0.00000
  en-unique b256 c64 t6 constrained cur w2-4            23.49  24   118.6    0.46   0.079  0.00    0.00002
  en-unique b256 c32 t5 constrained cur w2-4            24.71  25    96.4    0.38   0.128  0.00    0.00000
  en-unique b256 c16 t5 constrained cur w2-4            27.61  28    84.2    0.31   0.126  0.00    0.00001
  en-unique b256 c64 t5 free        cur w2-4            21.80  22   105.8    0.42   0.111  0.62    0.00000
  en-unique b128 c64 t5 free      nocur w2-4            21.61  22   104.9    0.44   0.081  0.65    0.00000
  en-fineweb-occ b256 c64 t5 free cur w2-4              24.36  25    94.3    0.21   0.179  0.60    0.00000
  tr-fineweb-occ b256 c64 t5 constrained nocur w2-4     22.72  23    96.9    0.20   0.018  0.00    0.00003

Pareto fronts (non-dominated on mean length, unattested, real-word share, nonend, fallback) are listed in report.html and lenmin_summary.json; with five dimensions most arms are non-dominated, so the
rule below picks one point. Comparisons across sources are not fair (different vocabulary training data and held-out text; English unique is a dictionary, FineWeb is running text).

Selection rule, fixed before looking at example phrases: among English unique-word arms with fallback share <= 1 percent and ending-constrained words, choose minimum exact mean length;
ties -> smaller max, then <= 5 tokens per word. (t6 is 0.11 chars shorter but exceeds the 5-token bound; it is rejected on that bound.)

Costs of design switches (paired over all English unique arms where both sides reach capacity):
- curated real one-token words: mean length changes by -0.31 chars on average (range -0.75..+0.22; 82 pairs). They cost nothing in length (they help, they are short) but remove 97 begin tokens that conflict with them under prefix-freeness (for example "th" is dropped when "the" is curated); the selected model keeps 36 curated words and 3.4 percent of generated words are one-token real words.
- ending constraint: +1.85 chars on average (range +1.17..+2.68; 78 pairs). Free endings are shorter because any token may stop a word, but 60-69 percent of words then end in a fragment that never ends words in the corpus. The selected arm pays the cost to keep proper word endings.

## Recommendation

Use lenmin v1 en-unique (selected arm) when length is the objective: 23.6 mean / 24 max characters for 64 bits, round trip tested. If readability proxies matter more, two near arms from the sweep: 4 words with up to 4 tokens
(23.92 mean, 25 max, real-word share 0.149 vs 0.060, unattested 0.40) or continuation cap 32 (24.71 / 25, unattested 0.38). Apply mix_v1 first for hash outputs and sequential counters. Do not use free endings unless length is the only criterion.

## Quality inspection (honest)

Examples (results/lenmin_examples.csv, 64 fixed inputs, each decoded and asserted in Rust; Python reference matches Rust on 20,000 samples x2 and the example rows, 0 mismatches). The selected output is mostly pronounceable pseudo-words
("huzigs headkurn phthmoan", "geoglovid fruir braxxcue", "rathrocis to nonycla it"), clearly less word-like than v4. Flags:
- raw small values are awkward and repetitive-looking by construction: 0 = "to to", 1 = "to of", 2 = "to is", 3 = "to it"; 4-char words dominate low values. Use mix_v1.
- odd fragments appear: "phth", "zyzd", "zurzd", "braxxcut", "kyzwah". The 1-token curated words are inserted between pseudo-words ("of", "it", "up", "us") in 3.4 percent of words.
- offensive-substring scan (listed English terms plus sex, damn, hell, crap, turd, pee, poo; substring matching, many false positives such as "pee" in "preejer"): 2.1 percent of 20k raw phrases and 2.2 percent of 20k mixed phrases contain a listed substring; one real hit in the first 5 mixed hits is "pornbut". No token blocklist exists in lenmin v1 builder; this is an open issue (add a token/word blocklist before shipping).
- repeated-word phrases: 0.03 percent raw, 0.015 percent mixed.
- DefaultHasher rows (hello, example, readable, "readable hash", ...) are illustrative only; DefaultHasher is not stable across Rust versions.
- no human or native-speaker validation was done.

## Rejected alternatives

- Fixed layouts (3+4+4, 4+4+4 tokens): longer (best fixed layout wastes the length-entropy of spaces).
- Free endings: shortest (21.6-21.8 mean) but 60-69 percent of words end in a non-ending fragment.
- 2-word phrases: no arm reaches 2^64 with <= 6 tokens/word without nonsense padding.
- 3 words exactly: +0.23 chars vs 2-4 words at the same bound; kept 2-4 as the selected word-count range because length-major ordering prefers more, shorter words (3 words 86 percent, 4 words 14 percent).
- Turkish and FineWeb arms: shown as sweep arms only (no frozen Rust model); FineWeb English has lower unattested rate (0.21) but is 0.8-2.7 chars longer in the same shape.
- Plain modulo/probabilistic suffixes/registries: not used (violate exactness).

## Open issues

- Quality gap versus real-word phrases; no human evaluation; raw ordering exposes short, repetitive phrases for low values.
- No obscenity blocklist; token-level filter needed. Curated real-word list is English only and small (36 curated words kept; a, i, an, in, he are dropped by prefix-free conflicts with and/her/inter; "ho" excluded as offensive).
- Variable word count 2-4 may be surprising to users; the 3-word arm is +0.23 chars.
- Mean length ~ max length (24) because the reachable set is dominated by the longest included length class; the distribution has a hard ceiling by construction.
- Model file is 284 KB; 200k encode+decode take 0.34 s in release (model parse time not separately measured).
- Sample proxies for the sweep use 5,000 values per arm (not exact); length statistics are exact.

## Reproducible commands

  cd /home/agent/projects/readable-hash-rs-reversible
  python3 models/overnight/test_lenmin.py                       # reduced exhaustive reference tests
  python3 models/overnight/architect_check.py                   # idealised token-count check
  python3 models/overnight/sweep_lenmin.py                      # 376-arm sweep (about 10 min, 3 processes); resumable
  python3 models/overnight/compile_lenmin.py --max-tokens 5 --cap-begin 256 --cap-cont 64 --ending constrained --words 2-4 --samples 20000 --export src/lenmin_models/en-unique.txt
  cargo test --all-features && cargo clippy --all-targets --all-features -- -D warnings && cargo fmt --all -- --check
  cargo run --release --example phrase_lenmin_comparison > models/overnight/results/lenmin_examples.csv
  python3 models/overnight/crosscheck_lenmin.py
  cargo run --release --example phrase_dyn_comparison -- --sample 200000 > /tmp/dynsample.tsv   # v4/dyn length sample
  python3 models/overnight/report_lenmin.py /tmp/dynsample.tsv   # needs report_partA.html from models/overnight/report.py

## Tests (Part B) and disk

- Rust (src/phrase_lenmin.rs): toy-automaton exhaustive bijection and length-major order, exhaustive decode of all strings up to length 5 over a 10-letter alphabet (images equal brute-force set), truncated-limit prefix property, invalid-model rejection, edge values (0, 1, 2, 42, 1000, 123456789, 2^63-1, 2^63, 2^64-2, 2^64-1), 100,000 deterministic round trips with uniqueness, length-major monotonicity of 100k sorted values, malformed/spacing/case negatives, mix/unmix composition, pinned vectors matching the Python reference.
- Python: lenmin.py reference tested exhaustively on the toy model; Rust vs Python cross-check (crosscheck_lenmin.py).
- Last run of everything: results/test_status.txt (all passing; clippy -D warnings exit 0).
- Disk: corpus 80 MB compressed outside git (/home/agent/corpora/readable-hash-overnight), target/ 1.9 GB, free space 93 GB; no new downloads in the continuation.

## Architect verification (morning re-run)

Re-ran independently: fmt check, cargo test --all-features (30 unit, 19/19 scenarios), clippy -D warnings, all Python tests, lenmin cross-check (40,128 encodings, 0 mismatches): all pass.

Missing quality comparison (same char-trigram judge as Part A, 20,000 seeded uniform values; lower = more English-like; real top-20k words = 3.47):

  codec            chars mean/max  char3 bits/char  real-word share
  v4               28.87 / 37      4.41             0.06%
  lenmin v1 raw    23.60 / 24      5.74             4.15%
  lenmin v1 + mix  23.60 / 24      5.76             3.98%

lenmin v1 is 18% shorter but markedly less English-like; pure length-major ranking prefers the shortest tokens regardless of quality. Next: rank by cost = letters + lambda * surprisal and sweep lambda.
