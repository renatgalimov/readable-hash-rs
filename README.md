[![Rust](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/rust.yml/badge.svg)](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/rust.yml)
[![Lint](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/lint.yml/badge.svg)](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/lint.yml)
[![Tests](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/tests.yml/badge.svg)](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/tests.yml)
[![Coverage](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/coverage.yml/badge.svg)](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/coverage.yml)
[![Fuzz](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/fuzz.yml/badge.svg)](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/fuzz.yml)
[![Semgrep](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/semgrep.yml/badge.svg)](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/semgrep.yml)
[![Crates.io](https://img.shields.io/crates/v/readable-hash.svg)](https://crates.io/crates/readable-hash)

# readable-hash-rs
Human-readable hashes for Rust, producing sentences in a made-up language.

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
