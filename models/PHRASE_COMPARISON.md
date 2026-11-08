# Phrase v2 versus experimental v3

V3 is English-only, incompatible with v2, and encodes a u64 exactly using
B128/M32/M32/E32 (22 bits) then twice B128/M32/M16/E32 (21 bits each).
Choices are least-significant first and context resets for each word. Tables are
prefix-free, exact-capacity, and validated. There is no suffix or registry.

Reproduce with `python models/compile_phrase.py --check`,
`python models/compile_phrase.py --v3 --check`, and
`python models/compare_phrases.py`. The last command independently traverses
both frozen models and writes `models/phrase_comparison.json`; exact rational
means and local/fallback probabilities, all examples, and differing beginning
IDs are there. The individual reports enumerate omitted observed choices for
every context; see `phrase_report.json` and `phrase_v3_report.json`.

The checked-in corpus has 94,080 unique words. Counts reconstruct token
transitions from those words, not running-text frequencies. Both compilers
choose locally observed transitions by summed corpus counts, then fill globally
by position-specific counts, constrained by exact prefix-free capacity. The
beginning selection uses viable local continuation connectivity, then beginning
frequency. Thirty of the 128 beginning IDs change between models, so effects
are not attributable to ending table size alone. The model is a heuristic, not
a readability optimization or natural-language probability model.

Uniform-u64 exact results (two spaces in addition to letters):

                          v2 E128            v3 E32
  phrase letters min/max  15 / 48            15 / 48
  phrase mean letters     28.37257194519043  26.982144355773926
  first-middle local      100% / 100%        100% / 100%
  second-middle local     99.2950% / 99.9756% 95.5269% / 99.2264%
  ending local            23.9754% / 23.9718% 81.0608% / 80.9595%

Each pair is word one / words two and three. Complement gives fallback; these
are reachable-path-weighted probabilities, not fractions averaged over rows.
Smaller ending tables substantially reduce ending fallback and the average
phrase is about 1.39 letters shorter, but second-middle locality falls and
examples remain artificial. Neither metric demonstrates improved human
readability; a human evaluation would be needed.

`cargo run --example phrase_comparison` hashes synthetic fixed strings with
`DefaultHasher::new()`, `write(input.as_bytes())`, and `finish()`, encodes both
formats, and asserts every example roundtrips. DefaultHasher output is not a
stable cross-Rust-version interchange guarantee. Example for `hello`:

  v2: computeves fervantish tankerton
  v3: crazader filianm subtencities
