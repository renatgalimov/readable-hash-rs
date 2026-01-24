# N-gram Model for Readable Hash Generation

This directory contains tools for training an n-gram language model that converts arbitrary bytes into pronounceable, English-like words.

## Overview

The system uses a position-aware tokenizer with 1024 tokens:
- **Beginning tokens** (0-255): Start of word, e.g., `^the`, `^un`, `^re`
- **End tokens** (256-511): End of word, e.g., `ing$`, `ed$`, `s$`
- **Middle tokens** (512-1023): Middle of word, e.g., `er`, `at`, `ion`

## Usage

### Train the Model

```bash
python3 tokenize.py training-data/english-lowercase.txt -o training-data/
```

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

## Files

- `tokenize.py` - Vocabulary builder, tokenizer, and model trainer
- `extract_words.py` - Extract unique words from corpus
- `test_tokenizer.py` - Test tokenization of words
- `training-data/` - Generated model files
- `corpus/` - Source text files (not tracked in git)
