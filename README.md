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

Generate a hash sentence:

```rust
use readable_hash::naive_readable_hash;

fn main() {
    let sentence = naive_readable_hash("hello");
    println!("{sentence}");
    // ungtoattmeertant dipresecorvisuch osfrom usellremight itthasiss upfeprojthem uthver off abljahim iz
}
```

More examples (StdHasher + `naive_readable_hash`):

```text
"I" -> "onlsuch popeall befons ig"
"a" -> "agrconsigweundaccsomthen "
"me" -> "ons ight ecekught ecelke"
"random" -> "gutexortught lient ugh ek"
"middle" -> "ent was ight rodonplacugh go"
"words" -> "men faend contitrepoem"
"supercalifragilisticexpialidocious" -> "ern takorduthpajabut he"
"pneumonoultramicroscopicsilicovolcanoconiosis" -> "dithem ittinhetleheag"
```

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
