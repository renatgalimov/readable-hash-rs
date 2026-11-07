[![Rust](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/rust.yml/badge.svg)](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/rust.yml)
[![Lint](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/lint.yml/badge.svg)](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/lint.yml)
[![Tests](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/tests.yml/badge.svg)](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/tests.yml)
[![Coverage](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/coverage.yml/badge.svg)](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/coverage.yml)
[![Fuzz](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/fuzz.yml/badge.svg)](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/fuzz.yml)
[![Semgrep](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/semgrep.yml/badge.svg)](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/semgrep.yml)
[![Crates.io](https://img.shields.io/crates/v/readable-hash.svg)](https://crates.io/crates/readable-hash)

# readable-hash-rs

Hashes like `a7b9c3d4e5f6...` are hard to read, compare, and remember. This crate transforms hash bytes into pronounceable text, making them easier on human eyes.

You might use this when verifying file integrity visually, or when you need consistent pseudonyms for names and addresses without caring much about cryptographic strength. It's also handy during debugging when you want to quickly tell hashes apart.

This crate is not trying to be the most secure, fastest, or most entropy-efficient solution. The goal is simply readability.

## Usage

Add the crate to your `Cargo.toml`:

```toml
readable-hash = "0.1"
```

Generate a readable hash:

```rust
use readable_hash::{english_word_hash, StdHasher};

fn main() {
    let word = english_word_hash::<StdHasher, _>("hello");
    println!("{word}");
    // thatised
}
```

More examples:

```text
"I" -> "waged"
"different" -> "imaumates"
"pneumonoultramicroscopicsilicovolcanoconiosis" -> "dummaricardemastria"
```

## Reversible u64 words

`encode_u64` and `decode_u64` implement a separate, stable version-1 format:

```rust
use readable_hash::{decode_u64, encode_u64};

let word = encode_u64(u64::MAX);
assert_eq!(decode_u64(&word), Some(u64::MAX));
assert_eq!(decode_u64("not-a-valid-word"), None);
```

This encodes a u64 losslessly; it is not a collision-free hash of arbitrary
inputs, an encryption scheme, or a guarantee of linguistic pronounceability.
The fixed-width token sequence can be long and sometimes awkward or repetitive.
The existing hash and word-generation APIs retain their old behavior.

The beginning index is `value % 179` and the quotient is `value / 179`.
Eleven 32-way middle choices store the quotient's low 55 bits, least significant
five-bit digit first; a 16-way ending stores the next four bits. The selected
token becomes the context for the next table. All choices are ordered
lexicographically by emitted text. The decoder parses one beginning, eleven
middles and one ending, then rejects trailing text and values above `u64::MAX`.
Most of the 59-bit quotient space is not reachable; not every table entry or
syntactically valid path occurs in a valid u64 word.

The versioned tables and vocabulary are frozen in `src/reversible_v1_data.rs`.
Each table is prefix-free after boundary markers are stripped. Thus the first
token determines a unique context, each subsequent token is uniquely parsed,
and the fixed token count and exact quotient reconstruction give an injective
encoding. Rust tests check every table, edge cases, a small exhaustive analogue,
100,000 deterministic distinct values, and v1 golden vectors.

To audit or reproduce the compiler and exact length metrics:

```sh
python models/compile_reversible.py --check
python models/reversible_metrics.py
python -m unittest discover -s models -v
```

The compiler retokenizes all 94,080 checked-in training words and verifies the
old quantized transitions. It chooses the maximum 179 prefix-free beginning
tokens from eligible beginnings, including the trainer's observed `x` fallback.
For each of 768 beginning/middle contexts it selects 32 middle and 16 ending
tokens from their separate 512- and 256-token pools. A trie dynamic program
maximizes local training weight, then global weight of nonlocal fill, then
chooses the lexicographically smallest token tuple, subject to prefix-freedom
and exact cardinality. Consequently some local tokens must be omitted: for
`^s`, 4 of 16 middle candidates (`ver`, `ze`, `ven`, `qui`) are omitted. The
complete per-context omission report is `models/reversible_v1_report.json`.
This prioritization does not imply frequency-weighted sampling of u64 values.

Dynamic programming over contexts and quotient bounds gives exact lengths of
13–47 letters for reachable u64 values; all syntactic table paths, including
out-of-range paths, span 13–48 letters. No expected length or backoff rate is
claimed. The decoder does not need a delimiter, suffix, or registry.

## Tokenizer

The `models/` directory bundles a small sample corpus and Python utilities for
training a BPE tokenizer with explicit word boundary markers using the
[`tokenizers`](https://github.com/huggingface/tokenizers) library.

Install dependencies and train the tokenizer:

```bash
pip install -r models/requirements.txt
python models/train_tokenizer.py models/sample_corpus.txt
```

This writes the tokenizer files into `models/tokenizer/`. You can verify that
the tokenizer works by encoding text with the helper script. The training
script normalizes input using Unicode NFKC and lowercases it prior to
tokenization, so differently cased forms produce the same tokens. Tokens that
continue a word are prefixed with `##`, while tokens finishing a word carry a
`</w>` suffix.

```bash
python models/tokenizer_check.py models/tokenizer/tokenizer.json "Hello WORLD"
```

## N-gram model

With a tokenizer trained, an n-gram language model can be built from the
corpus:

```bash
python models/train_ngram.py models/sample_corpus.txt
```

Pass `-n` to control the order (default 2 for bigrams).

The tokenizer must define start (`<s>`) and end (`</s>`) tokens, which the
script uses to mark sentence boundaries. It also verifies that tokens respect
word-boundary markers (`##` prefixes and `</w>` suffixes) before accumulating
statistics. The result is written to ``ngram.json`` and stores transition
probabilities between token ids.

## Generating the 8-bit model

Use the built-in tokenizer/trainer to produce a JSON model with 8-bit
cumulative thresholds (0..=255):

```bash
python models/tokenize.py models/sample_corpus.txt -o training-data
```

This writes `training-data/<input>-model.json` with 8-bit cumulative transition
tables and includes `probability_resolution_bits: 8` in the metadata.

## Entropy consumption and weighted transitions (8-bit)

The Rust generator turns a fixed byte slice of entropy into a sequence of
tokens by repeatedly sampling transitions from a weighted distribution encoded
as cumulative probabilities with 8-bit resolution.

**Entropy consumption**
- A `BitReader` wraps the entropy bytes and exposes a bit cursor.
- Each token choice reads 8 bits, yielding a value in `0..=255`. If fewer than
  8 bits remain, generation stops (or falls back to a default for the end
  token).
- Using 8-bit chunks reduces entropy usage per step and matches the transition
  tables’ resolution.

**Weighted transition selection**
- Transitions are stored as `(token_id, cumulative_probability)` pairs with
  cumulative values in `0..=255` (u8).
- Given an 8-bit value, the code selects the first entry whose cumulative
  probability is greater than or equal to the value. If no entry matches (a
  safety fallback), it returns the last token.
- For example, with two options `(A, 127)` and `(B, 255)`, values `0..=127`
  yield `A`, and `128..=255` yield `B`.

In summary: entropy is consumed in fixed 8-bit chunks, and those chunks are
interpreted through cumulative probability tables to pick the next token.
