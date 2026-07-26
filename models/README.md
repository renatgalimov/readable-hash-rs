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

### 5) Build n-gram counts

The model is a flat n-gram table over token IDs (size configurable):

- `ngrams`: counts of fixed-length token sequences. Short prefixes are left
  padded with `null` to reach `ngram_size`.
- `end_ngrams`: counts of fixed-length token sequences whose final token is
  an end token.

### 6) Convert to quantized probability tables

For each list, counts are converted to quantized integer weights (based on
`probability_resolution_bits`) and sorted by descending frequency.

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
- `ngrams`: Flat list of n-gram sequences with quantized weights
- `end_ngrams`: Flat list of end-token n-gram sequences with quantized weights
 - `temperature`: Temperature used to smooth token probabilities
 - `smoothing_alpha`: Additive smoothing applied per context

### N-gram Size

The model uses a fixed n-gram size, configured at training time:

```bash
python3 tokenize.py corpus/ -o training-data/ --ngram-size 4
```

This value is stored in the output JSON as `ngram_size`.

### Probability Resolution Bits

Probabilities are quantized into integer weights using the requested resolution:

```bash
python3 tokenize.py corpus/ -o training-data/ --probability-bits 10
```

The quantized range is `0..(2^probability_resolution_bits - 1)` and the weights
sum to the maximum value within each selection context.

### Temperature

Temperature smooths the distribution before quantization:

```bash
python3 tokenize.py corpus/ -o training-data/ --temperature 1.5
```

Values greater than 1.0 flatten the distribution, values below 1.0 sharpen it.

### Additive Smoothing

Additive smoothing ensures every token observed in a context retains some
probability after quantization:

```bash
python3 tokenize.py corpus/ -o training-data/ --smoothing-alpha 1.0
```

### Generate Words from Bytes

The model converts entropy (bytes) into English-like words using quantized weights.

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

1. **Select tokens**: Use the last `ngram_size - 1` tokens (left
   padded with `null`) to select from `ngrams`
2. **Select end token**: Use the same context to select from `end_ngrams`

The probability format is quantized:
```json
{
  "ngrams": [[[id_or_null, id_or_null, id], weight], ...],
  "end_ngrams": [[[id_or_null, id_or_null, end_id], weight], ...]
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

This generates `../src/english_word_data.rs` containing:
- Static token vocabulary
- Transition tables for generation functions

Note: `generate_rust.py` currently expects the legacy transition format.

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
