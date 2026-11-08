# English phrase v3 versus experimental v4

V4 is an incompatible, reversible encoding, not encryption. It keeps the v3
beginning, M32, M16 and E32 tables byte-for-byte, including the v3 beginning
optimization. Only word 3 changes: B128/M32/M16/E32 becomes
B128/M32/M32/E16. Words 1 and 2 stay B128/M32/M32/E32 and
B128/M32/M16/E32. The 22+21+21 bits are read least-significant first; context
resets per word. All rows retain exact cardinality and prefix-free spellings.
E16 is independently chosen per context with the existing local-weight-first,
then global-fill optimizer. `phrase_v4_end16.json` records omitted local tokens.

Reproduce and check without overwriting: `python models/compile_phrase.py --check`,
`python models/compile_phrase.py --v3 --check`,
`python models/compile_phrase_v4.py --check`, and
`python models/compare_phrase_v4.py --check`. Omit `--check` on the last two
to regenerate their artifacts. `cargo run --example phrase_v4_comparison`
prints the synthetic examples; `hello` uses DefaultHasher::new(), write(b"hello"),
finish(). DefaultHasher is not a stable cross-Rust-version interchange format.

Uniform-u64 exact results use 94,080 unique corpus words, not running text.
Local means the context-to-token adjacency occurred in that list; fallback means
it did not. Probabilities weight reachable paths, not rows. Phrase-level
probabilities below average the three word positions equally for each transition
position. See `phrase_v4_comparison.json` for exact fractions and path counts.

                         v3                 v4
Third word min/max       5 / 16             5 / 16 letters
Third word mean          18869225/2097152   9312985/1048576
Phrase min/max           15 / 48            15 / 48 letters
Phrase mean              28292829/1048576   56342403/2097152
                         26.9821443558      26.8661513329

Third word locality / fallback:
                         v3                 v4
First middle             1 / 0              1 / 0
Second middle            65029/65536        125209/131072
 fallback                507/65536          5863/131072
Ending                   424461/524288      2036669/2097152
 fallback                99827/524288       60483/2097152

Full phrase locality / fallback, averaged across word positions:
                         v3                 v4
First middle             1 / 0              1 / 0
Second middle            385325/393216      95119/98304
 fallback                7891/393216        3185/98304
Ending                   5095657/6291456    905747/1048576
 fallback                1195799/6291456    142829/1048576

The third ending becomes more local, while its second middle becomes less local;
the phrase is slightly shorter on average. These are corpus-adjacency metrics,
not proof of readability or of natural-language likelihood; human evaluation is
needed. No claim of repetition avoidance is made: at zero v3 repeats words 2/3,
whereas v4 repeats words 1/3. At u64::MAX v3 repeats words 2/3, whereas v4's
three words differ. Other inputs may repeat.

Actual examples (input | v3 | v4):

    0 | abandaia abandaal abandaal | abandaia abandaal abandaia
    1 | adaiaca abandaal abandaal | adaiaca abandaal abandaia
    2 | alarbable abandaal abandaal | alarbable abandaal abandaia
    42 | exactaca abandaal abandaal | exactaca abandaal abandaia
    1000 | shaemada abandaal abandaal | shaemada abandaal abandaia
    123456789 | certiwking couchaberal abandaal | certiwking couchaberal abandaia
    9223372036854775807 | woundzz woundruz woundruing | woundzz woundruz woundzine
    9223372036854775808 | abandaia abandaal abandaion | abandaia abandaal abandaims
    18446744073709551614 | wizzz woundruz woundruz | wizzz woundruz woundzy
    18446744073709551615 | woundzz woundruz woundruz | woundzz woundruz woundzy
    2611923443488327891 | orierling chairasseth steinomat | orierling chairasseth steinctare
    16045690984503098046 | jerredy favoureth hereivate | jerredy favoureth hereivation
    hello (16350172494705860510) | crazader filianm subtencities | crazader filianm subtencium

Tests include all golden vectors above, canonical rejection and truncation,
100,000 distinct deterministic u64 roundtrips and phrase uniqueness, unchanged
first two words against v3, 4,096 exhaustive one-bit-per-token combinations
through the real codec, table invariants and deterministic regeneration. Legacy
v1/v2/v3 tests and goldens remain in the full suite.
