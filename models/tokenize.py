#!/usr/bin/env python3
"""Train a position-aware tokenizer and build an n-gram model for word beginnings.

Token ID layout:
- 0-255: beginning tokens (^a, ^th, ^un, ...)
- 256-511: end tokens (a$, s$, ing$, ...)
- 512-1023: middle tokens (a, e, th, ...)

Total vocabulary size: 1024

The n-gram model captures fixed-length token sequences.
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


def quantize_counts(
    counts: Counter[int],
    max_value: int,
    temperature: float,
    smoothing_alpha: float,
) -> list[tuple[int, int]]:
    """Quantize counts into integer weights that sum to max_value."""
    if not counts:
        return []
    if temperature <= 0:
        raise ValueError("temperature must be greater than 0")
    if smoothing_alpha < 0:
        raise ValueError("smoothing_alpha must be >= 0")
    exponent = 1.0 / temperature
    adjusted: list[tuple[int, float]] = []
    adjusted_map: dict[int, float] = {}
    for token_id, count in counts.items():
        weight = (float(count) + smoothing_alpha) ** exponent
        adjusted.append((token_id, weight))
        adjusted_map[token_id] = weight
    items = sorted(adjusted, key=lambda item: -item[1])
    bases: list[tuple[int, int, float]] = []
    adjusted_total = sum(weight for _, weight in items)
    if adjusted_total <= 0:
        return []
    if max_value < len(items):
        base_total = 0
        for token_id, weight in items:
            exact = weight * max_value / adjusted_total
            base = int(exact)
            base_total += base
            bases.append((token_id, base, exact - base))
    else:
        base_total = len(items)
        remaining_pool = max_value - base_total
        for token_id, weight in items:
            exact = weight * remaining_pool / adjusted_total
            base = 1 + int(exact)
            base_total += base - 1
            bases.append((token_id, base, exact - int(exact)))
    remaining = max_value - base_total
    if remaining > 0:
        bases.sort(key=lambda item: item[2], reverse=True)
        for index in range(remaining):
            token_id, base, remainder = bases[index]
            bases[index] = (token_id, base + 1, remainder)
        bases.sort(key=lambda item: -adjusted_map[item[0]])
    return [(token_id, weight) for token_id, weight, _ in bases]


def build_ngram_quantized_list(
    ngram_counts: Counter[tuple[int | None, ...]],
    max_value: int,
    temperature: float,
    smoothing_alpha: float,
) -> list[list[object]]:
    """Convert n-gram counts to a flat list of [ngram, weight]."""
    if not ngram_counts:
        return []
    context_counts: dict[tuple[int | None, ...], Counter[int | None]] = defaultdict(Counter)
    for ngram, count in ngram_counts.items():
        context = ngram[:-1]
        next_token = ngram[-1]
        context_counts[context][next_token] += count

    result: list[list[object]] = []
    def sort_key(value: tuple[int | None, ...]) -> tuple[int, ...]:
        return tuple(-1 if item is None else item for item in value)

    for context in sorted(context_counts.keys(), key=sort_key):
        quantized = quantize_counts(
            context_counts[context],
            max_value,
            temperature,
            smoothing_alpha,
        )
        for next_token, weight in quantized:
            ngram = list(context) + [next_token]
            result.append([ngram, weight])
    return result


def is_end_token(token_id: int) -> bool:
    return NUM_BEGINNING_TOKENS <= token_id < NUM_BEGINNING_TOKENS + NUM_END_TOKENS


def main():
    parser = argparse.ArgumentParser(
        description="Train a position-aware tokenizer and build n-gram model"
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
    parser.add_argument(
        "-n",
        "--ngram-size",
        type=int,
        default=2,
        help="N-gram size for the model (default: 2)",
    )
    parser.add_argument(
        "-p",
        "--probability-bits",
        type=int,
        default=8,
        help="Probability resolution bits for quantized weights (default: 8)",
    )
    parser.add_argument(
        "-t",
        "--temperature",
        type=float,
        default=1.0,
        help="Temperature for smoothing token probabilities (default: 1.0)",
    )
    parser.add_argument(
        "--smoothing-alpha",
        type=float,
        default=0.0,
        help="Additive smoothing for token counts per context (default: 0.0)",
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
    ngram_counts: Counter[tuple[int | None, ...]] = Counter()
    end_ngram_counts: Counter[tuple[int | None, ...]] = Counter()

    skipped_words = 0
    ngram_size = args.ngram_size
    if ngram_size < 1:
        print("Error: n-gram size must be at least 1")
        return 1

    probability_bits = args.probability_bits
    if probability_bits < 1:
        print("Error: probability resolution bits must be at least 1")
        return 1
    temperature = args.temperature
    if temperature <= 0:
        print("Error: temperature must be greater than 0")
        return 1
    smoothing_alpha = args.smoothing_alpha
    if smoothing_alpha < 0:
        print("Error: smoothing alpha must be >= 0")
        return 1
    max_probability_value = (1 << probability_bits) - 1

    for word in all_words:
        tokens = tokenize_word(word, vocab)
        if not tokens:
            continue

        try:
            token_ids = [vocab[token] for token in tokens]
        except KeyError:
            skipped_words += 1
            continue

        for position_index in range(len(token_ids)):
            ngram: list[int | None] = []
            start_index = position_index - (ngram_size - 1)
            for history_index in range(start_index, position_index + 1):
                if history_index < 0:
                    ngram.append(None)
                else:
                    ngram.append(token_ids[history_index])
            ngram_counts[tuple(ngram)] += 1
            if is_end_token(token_ids[position_index]):
                end_ngram_counts[tuple(ngram)] += 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    base_name = input_files[0].stem if args.input else "stdin"

    id_to_token = {token_id: token for token, token_id in vocab.items()}
    id_to_token_list = [id_to_token.get(i, f"[UNK:{i}]") for i in range(TOTAL_VOCAB_SIZE)]

    model_data = {
        "version": "2.0",
        "probability_resolution_bits": probability_bits,
        "ngram_size": args.ngram_size,
        "temperature": temperature,
        "smoothing_alpha": smoothing_alpha,
        "total_words": len(all_words),
        "vocab": vocab,
        "id_to_token": id_to_token_list,
        "ngrams": build_ngram_quantized_list(
            ngram_counts, max_probability_value, temperature, smoothing_alpha
        ),
        "end_ngrams": build_ngram_quantized_list(
            end_ngram_counts, max_probability_value, temperature, smoothing_alpha
        ),
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
    print(f"N-grams: {len(model_data['ngrams'])} sequences")
    print(f"End n-grams: {len(model_data['end_ngrams'])} sequences")
    print(f"Saved model to {model_path}")


if __name__ == "__main__":
    main()
