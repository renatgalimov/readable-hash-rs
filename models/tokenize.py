#!/usr/bin/env python3
"""Train a position-aware tokenizer and build a bigram model for word beginnings.

Token ID layout:
- 0-255: beginning tokens (^a, ^th, ^un, ...)
- 256-511: end tokens (a$, s$, ing$, ...)
- 512-1023: middle tokens (a, e, th, ...)

Total vocabulary size: 1024

The bigram model captures: beginning_token -> next_token transitions.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

BOS = "^"
EOS = "$"
NUM_BEGINNING_TOKENS = 256
NUM_END_TOKENS = 256
NUM_MIDDLE_TOKENS = 512
TOTAL_VOCAB_SIZE = NUM_BEGINNING_TOKENS + NUM_END_TOKENS + NUM_MIDDLE_TOKENS

MAX_TOKENS_PER_WORD = 16
MIN_TOKENS_PER_WORD = 2
BITS_PER_TOKEN_ESTIMATE = 8


def extract_words(text: str) -> list[str]:
    """Extract lowercase words from text."""
    return re.findall(r"[a-z]+", text.lower())


def collect_ngram_counts(
    words: list[str], max_ngram: int = 6
) -> tuple[Counter[str], Counter[str], Counter[str]]:
    """Collect n-gram counts for beginning, end, and middle positions."""
    beginning_counts: Counter[str] = Counter()
    end_counts: Counter[str] = Counter()
    middle_counts: Counter[str] = Counter()

    for word in words:
        if len(word) == 0:
            continue

        for ngram_len in range(1, min(max_ngram + 1, len(word) + 1)):
            beginning_ngram = f"{BOS}{word[:ngram_len]}"
            beginning_counts[beginning_ngram] += 1

            end_ngram = f"{word[-ngram_len:]}{EOS}"
            end_counts[end_ngram] += 1

        for start_pos in range(1, len(word) - 1):
            for ngram_len in range(1, min(max_ngram + 1, len(word) - start_pos)):
                if start_pos + ngram_len < len(word):
                    middle_ngram = word[start_pos : start_pos + ngram_len]
                    middle_counts[middle_ngram] += 1

    return beginning_counts, end_counts, middle_counts


def build_vocabulary(
    beginning_counts: Counter[str],
    end_counts: Counter[str],
    middle_counts: Counter[str],
) -> dict[str, int]:
    """Build vocabulary with exactly 1024 tokens in position-based ID ranges."""
    vocab: dict[str, int] = {}

    top_beginning = beginning_counts.most_common(NUM_BEGINNING_TOKENS)
    for idx, (token, _) in enumerate(top_beginning):
        vocab[token] = idx
    for idx in range(len(top_beginning), NUM_BEGINNING_TOKENS):
        vocab[f"[UNUSED_BEG_{idx}]"] = idx

    top_end = end_counts.most_common(NUM_END_TOKENS)
    for idx, (token, _) in enumerate(top_end):
        vocab[token] = NUM_BEGINNING_TOKENS + idx
    for idx in range(len(top_end), NUM_END_TOKENS):
        vocab[f"[UNUSED_END_{idx}]"] = NUM_BEGINNING_TOKENS + idx

    middle_offset = NUM_BEGINNING_TOKENS + NUM_END_TOKENS
    top_middle = middle_counts.most_common(NUM_MIDDLE_TOKENS)
    for idx, (token, _) in enumerate(top_middle):
        vocab[token] = middle_offset + idx
    for idx in range(len(top_middle), NUM_MIDDLE_TOKENS):
        vocab[f"[UNUSED_MID_{idx}]"] = middle_offset + idx

    return vocab


def tokenize_word(word: str, vocab: dict[str, int]) -> list[str]:
    """Tokenize a word using greedy longest-match with position awareness."""
    if len(word) == 0:
        return []

    tokens = []
    position = 0

    while position < len(word):
        is_beginning = position == 0
        is_end = position == len(word) - 1

        best_token = None
        best_length = 0

        for length in range(min(6, len(word) - position), 0, -1):
            substring = word[position : position + length]

            if is_beginning and position + length == len(word):
                candidate = f"{BOS}{substring}{EOS}"
                if candidate in vocab:
                    best_token = candidate
                    best_length = length
                    break

            if is_beginning:
                candidate = f"{BOS}{substring}"
                if candidate in vocab:
                    best_token = candidate
                    best_length = length
                    break
                continue

            if position + length == len(word):
                candidate = f"{substring}{EOS}"
                if candidate in vocab:
                    best_token = candidate
                    best_length = length
                    break

            if substring in vocab:
                best_token = substring
                best_length = length
                break

        if best_token is None:
            char = word[position]
            if is_beginning:
                candidate = f"{BOS}{char}"
                if candidate in vocab:
                    best_token = candidate
                elif char in vocab:
                    best_token = char
                else:
                    best_token = candidate
            elif is_end:
                candidate = f"{char}{EOS}"
                if candidate in vocab:
                    best_token = candidate
                elif char in vocab:
                    best_token = char
                else:
                    best_token = candidate
            else:
                best_token = char
            best_length = 1

        tokens.append(best_token)
        position += best_length

    return tokens


def build_cumulative_list(counts: Counter[int]) -> list[list[int]]:
    """Convert counts to cumulative thresholds in 0..=255 sorted by frequency."""
    total = sum(counts.values())
    if total == 0:
        return []
    items = sorted(counts.items(), key=lambda item: -item[1])
    cumulative_count = 0
    last_threshold = 0
    result: list[list[int]] = []
    for token_id, count in items:
        cumulative_count += count
        threshold = round(cumulative_count * 255 / total)
        if threshold < last_threshold:
            threshold = last_threshold
        if threshold > 255:
            threshold = 255
        result.append([token_id, threshold])
        last_threshold = threshold
    result[-1][1] = 255
    return result


def build_cumulative_transitions(
    counts: dict[int, Counter[int]],
) -> dict[str, list[list[int]]]:
    """Convert transition counts to cumulative threshold dict."""
    result: dict[str, list[list[int]]] = {}
    for token_id, next_counts in counts.items():
        cumulative_list = build_cumulative_list(next_counts)
        if cumulative_list:
            result[str(token_id)] = cumulative_list
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Train a position-aware tokenizer and build bigram model"
    )
    parser.add_argument(
        "input",
        nargs="*",
        type=Path,
        help="Input text files (reads from stdin if none provided)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("training-data"),
        help="Output directory (default: training-data)",
    )
    args = parser.parse_args()

    input_files: list[Path] = []
    temp_file = None

    if args.input:
        for filepath in args.input:
            if filepath.is_file():
                input_files.append(filepath)
            elif filepath.is_dir():
                input_files.extend(filepath.glob("**/*.txt"))
    else:
        temp_file = args.output_dir / "temp_input.txt"
        args.output_dir.mkdir(parents=True, exist_ok=True)
        temp_file.write_text(sys.stdin.read(), encoding="utf-8")
        input_files.append(temp_file)

    if not input_files:
        print("Error: No input files found")
        return 1

    all_words: list[str] = []
    for filepath in input_files:
        text = filepath.read_text(encoding="utf-8", errors="ignore")
        words = extract_words(text)
        all_words.extend(words)

    if temp_file and temp_file.exists():
        temp_file.unlink()

    print(f"Collecting n-gram statistics from {len(all_words)} words...")
    beginning_counts, end_counts, middle_counts = collect_ngram_counts(all_words)

    print("Building vocabulary...")
    vocab = build_vocabulary(beginning_counts, end_counts, middle_counts)

    print("Building transition models...")
    begin_counts: Counter[int] = Counter()
    transition_counts: dict[int, Counter[int]] = defaultdict(Counter)
    end_transition_counts: dict[int, Counter[int]] = defaultdict(Counter)

    skipped_words = 0
    for word in all_words:
        tokens = tokenize_word(word, vocab)
        if not tokens:
            continue

        try:
            token_ids = [vocab[token] for token in tokens]
        except KeyError:
            skipped_words += 1
            continue

        begin_counts[token_ids[0]] += 1

        for index in range(len(token_ids) - 1):
            current_id = token_ids[index]
            next_id = token_ids[index + 1]

            if NUM_BEGINNING_TOKENS <= next_id < NUM_BEGINNING_TOKENS + NUM_END_TOKENS:
                end_transition_counts[current_id][next_id] += 1
            else:
                transition_counts[current_id][next_id] += 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    base_name = input_files[0].stem if args.input else "stdin"

    id_to_token = {token_id: token for token, token_id in vocab.items()}
    id_to_token_list = [id_to_token.get(i, f"[UNK:{i}]") for i in range(TOTAL_VOCAB_SIZE)]

    model_data = {
        "version": "1.1",
        "probability_resolution_bits": 8,
        "total_words": len(all_words),
        "vocab": vocab,
        "id_to_token": id_to_token_list,
        "begin_transitions": build_cumulative_list(begin_counts),
        "transitions": build_cumulative_transitions(transition_counts),
        "end_transitions": build_cumulative_transitions(end_transition_counts),
    }
    model_path = args.output_dir / f"{base_name}-model.json"
    model_path.write_text(json.dumps(model_data, indent=2), encoding="utf-8")

    actual_beginning = sum(1 for token in vocab if token.startswith(BOS))
    actual_end = sum(1 for token in vocab if token.endswith(EOS) and not token.startswith(BOS))
    actual_middle = len(vocab) - actual_beginning - actual_end

    print(f"Vocabulary size: {len(vocab)}")
    print(f"  Beginning tokens (0-255): {actual_beginning}")
    print(f"  End tokens (256-511): {actual_end}")
    print(f"  Middle tokens (512-1023): {actual_middle}")
    print(f"Total words processed: {len(all_words)}")
    if skipped_words > 0:
        print(f"Skipped words (unknown tokens): {skipped_words}")
    print(f"Begin transitions: {len(model_data['begin_transitions'])} beginning tokens")
    print(f"Middle transitions: {len(model_data['transitions'])} tokens have next-token data")
    print(f"End transitions: {len(model_data['end_transitions'])} tokens have end-token data")
    print(f"Saved model to {model_path}")


if __name__ == "__main__":
    main()
