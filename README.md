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

## Training data and models

The `models/` directory contains the current tokenizer, n-gram trainer, and
model conversion utilities. The workflow uses a position-aware tokenizer and
8-bit cumulative probability tables. For full details, see
`models/README.md`.

To train a model from text files and emit a JSON model with 8-bit cumulative
thresholds:

```bash
python3 models/tokenize.py models/training-data/english-lowercase.txt -o models/training-data/
```

To convert that model into Rust source for the crate:

```bash
python3 models/generate_rust.py models/training-data/english-lowercase-model.json
```

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
