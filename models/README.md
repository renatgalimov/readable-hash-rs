# N-gram Model for Readable Hash Generation

This directory contains tools for training an n-gram language model that converts arbitrary bytes into pronounceable, English-like words.

## Overview

The system uses a position-aware tokenizer with 1024 tokens:
- **Beginning tokens** (0-255): Start of word, e.g., `^the`, `^un`, `^re`
- **End tokens** (256-511): End of word, e.g., `ing$`, `ed$`, `s$`
- **Middle tokens** (512-1023): Middle of word, e.g., `er`, `at`, `ion`

## Algorithm Details

### 1) Extract words

The trainer lowercases text and extracts alphabetic words only:

- Regex: `[a-z]+`
- Non-ASCII letters and punctuation are ignored.

### 2) Collect n-gram counts

For each word, the trainer counts n-grams up to length 6:

- **Beginning n-grams:** `^` + prefix of length 1..6
- **End n-grams:** suffix of length 1..6 + `$`
- **Middle n-grams:** all substrings that start after the first character and
  end before the last character

This yields three frequency tables: beginning, middle, and end.

### 3) Build a fixed-size vocabulary (1024 tokens)

The vocabulary is built by frequency within each position class:

- Top 256 beginning tokens (0–255); unused slots are filled with
  `[UNUSED_BEG_*]`.
- Top 256 end tokens (256–511); unused slots are filled with
  `[UNUSED_END_*]`.
- Top 512 middle tokens (512–1023); unused slots are filled with
  `[UNUSED_MID_*]`.

The `id_to_token` array is derived from the vocabulary so IDs are contiguous.

### 4) Tokenize words (greedy, position-aware)

Each word is tokenized using greedy longest-match up to 6 characters:

1. At each position, try the longest candidate substring.
2. If at the beginning, prefer `^substring` tokens.
3. If at the end, prefer `substring$` tokens.
4. If the entire word fits, allow `^substring$`.
5. If no candidate is found, fall back to a single-character token.

This produces a token sequence per word, typically 2–16 tokens.

### 5) Build transition counts

The model is a bigram transition table over token IDs:

- `begin_transitions`: frequency of first tokens in each word.
- `transitions`: counts for token → token where the next token is **not** an end
  token.
- `end_transitions`: counts for token → end-token.

### 6) Convert to cumulative probability tables

For each transition list, counts are converted to cumulative probabilities and
sorted by descending frequency. This enables binary search over cumulative
probabilities during generation.

## Usage

### Build a Generator Model

```bash
python3 tokenize.py training-data/english-lowercase.txt -o training-data/
```

`tokenize.py` accepts one or more `.txt` files or directories. If you pass a
directory, it will scan `**/*.txt`. If you pass no input files, it reads from
stdin.

```bash
# multiple input files
python3 tokenize.py corpus/a.txt corpus/b.txt -o training-data/

# directory input
python3 tokenize.py corpus/ -o training-data/

# stdin input
cat corpus/a.txt | python3 tokenize.py -o training-data/
```

The output model filename is based on the first input file stem (or `stdin`).
This generates `training-data/english-lowercase-model.json` containing:
- `vocab`: Token to ID mapping
- `id_to_token`: ID to token mapping (array)
- `begin_transitions`: Cumulative probabilities for first token selection
- `transitions`: Token-to-token transition probabilities
- `end_transitions`: Token-to-end-token transition probabilities

### Generate Words from Bytes

The model converts entropy (bytes) into English-like words using cumulative probability distributions.

**Example: 0xDEADBEEF (4 bytes)**
```
Input:  0xDEADBEEF
Output: snattenotional
```

**Example: 0xDEADBEEFCAFE (6 bytes)**
```
Input:  0xDEADBEEFCAFE
Output: snattenotlausece
```

### Word Generation Algorithm

1. **Select beginning token**: Use first 8 bits to index into `begin_transitions`
2. **Select middle tokens**: For each token, use bits to select from `transitions[current_token]`
3. **Select end token**: Use remaining bits to select from `end_transitions[current_token]`

The cumulative probability format enables O(log n) binary search:
```json
{
  "begin_transitions": [[token_id, cumulative_prob], ...],
  "transitions": {"token_id": [[next_id, cumulative_prob], ...]},
  "end_transitions": {"token_id": [[end_id, cumulative_prob], ...]}
}
```

### Output Length

Word length scales with input bytes:
| Input Bytes | Approximate Tokens |
|-------------|-------------------|
| 1           | 2                 |
| 2           | 3                 |
| 4           | 6                 |
| 6           | 8                 |
| 8           | 10                |
| 16          | 16 (max)          |

## Generate Rust Code

Convert the model to Rust code for use in the library:

```bash
python3 generate_rust.py training-data/english-lowercase-model.json
```

This generates `../src/english_word.rs` containing:
- Static token vocabulary
- Transition tables with cumulative probabilities
- `generate_word()` function for word generation

### Rust API

```rust
use readable_hash::english_word_hash;

let words = english_word_hash("hello");
// "basember durangle misinual sancture execony weary"
```

## Files

- `tokenize.py` - Vocabulary builder, tokenizer, and model trainer
- `generate_rust.py` - Generate Rust code from model
- `extract_words.py` - Extract unique words from corpus
- `test_tokenizer.py` - Test tokenization of words
- `training-data/` - Generated model files
- `corpus/` - Source text files (not tracked in git)
