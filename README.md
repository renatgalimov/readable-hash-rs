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
the tokenizer works by encoding text with the helper script:

```bash
python models/tokenizer_check.py models/tokenizer/tokenizer.json "hello world"
```
