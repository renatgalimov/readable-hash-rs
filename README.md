[![Rust](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/rust.yml/badge.svg)](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/rust.yml)
[![Lint](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/lint.yml/badge.svg)](https://github.com/renatgalimov/readable-hash-rs/actions/workflows/lint.yml)

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
training a Byte-Level BPE tokenizer using the
[`tokenizers`](https://github.com/huggingface/tokenizers) library.

Install dependencies and train the tokenizer:

```bash
pip install -r models/requirements.txt
python models/train_tokenizer.py models/sample_corpus.txt
```

This writes the tokenizer files into `models/tokenizer/`. You can verify that
the tokenizer works by encoding text with the helper script. The training
script normalizes input using Unicode NFKC and lowercases it prior to
tokenization, so differently cased forms produce the same tokens:

```bash
python models/tokenizer_check.py models/tokenizer/tokenizer.json "Hello WORLD"
```

## Bigram model

With a tokenizer trained, a simple bigram language model can be built from the
corpus:

```bash
python models/train_bigram.py models/tokenizer/tokenizer.json models/sample_corpus.txt
```

The tokenizer must define start (`<s>`) and end (`</s>`) tokens, which the
script uses to mark boundaries when computing bigram transitions. It writes
``bigram.json`` containing transition probabilities between token ids.
