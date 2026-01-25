---
name: readable-hash-models
description: Create or update readable-hash generator models in this repo from corpus files (models/corpus). Use when asked to build new models, generate Rust modules, expose new hash functions, or add tests for corpus-based readable hashes with task-specific n-gram sizes.
---

# Readable Hash Model Creation

## Quick start

1) Confirm requirements
- Identify corpus file(s) in `models/corpus/`.
- Identify target n-gram size for this task (any integer).
- Identify desired Rust module + function names and output behavior (word list vs sentence, separators, max length).

2) Prepare corpus
- Ensure the corpus is plain text in English.
- If the input is Project Gutenberg, use `models/bin/prepare_gutenberg_corpus.sh` to strip headers/footers.

3) Train model
- Run `python3 models/tokenize.py <inputs> -o models/training-data/`.
- If the task requires a different n-gram size, update `models/tokenize.py` to accept a CLI option (e.g. `--max-ngram`) and use a descriptive variable name. Avoid single-letter names except `i`, `j`, `k`.
- Update `models/README.md` if new flags or behaviors are added.

4) Generate Rust
- Run `python3 models/generate_rust.py models/training-data/<name>-model.json`.
- Write output to `src/<model_name>.rs` alongside `src/english_word.rs`.
- Ensure the generated Rust file embeds the model data and exposes a function
  that generates the readable hash output for that model.

5) Wire public API
- Expose a new function in `src/lib.rs` that mirrors `english_word_hash` style.
- Keep API naming consistent with the requested model.

6) Tests
- Add Cucumber feature files under `tests/features/`.
- Update `tests/cucumber.rs` step definitions if the new API needs coverage.

7) Verify
- Run `cargo fmt --all` and `cargo test`.

## References to read when needed

- `models/README.md` for model format and generation flow.
- `models/tokenize.py` for tokenization + model training behavior.
- `models/generate_rust.py` for Rust code generation details.
- `src/english_word.rs` and `src/lib.rs` for API patterns.
- `tests/features/*.feature` and `tests/cucumber.rs` for testing patterns.
