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
