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
            if is_beginning:
                best_token = f"{BOS}{word[position]}"
            elif is_end:
                best_token = f"{word[position]}{EOS}"
            else:
                best_token = word[position]
            best_length = 1

        tokens.append(best_token)
        position += best_length

    return tokens


def get_beginning_bigram(tokens: list[str]) -> tuple[str, str] | None:
    """Get the beginning bigram (first two tokens) only if second is not an end token."""
    if len(tokens) < 2:
        return None
    if tokens[1].endswith(EOS):
        return None
    return (tokens[0], tokens[1])


def get_beginning_end_bigram(tokens: list[str]) -> tuple[str, str] | None:
    """Get beginning-end bigram only if word has exactly 2 tokens and second is an end token."""
    if len(tokens) != 2:
        return None
    if not tokens[1].endswith(EOS):
        return None
    return (tokens[0], tokens[1])


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

    print("Building bigram models...")
    beginning_next_counts: dict[str, Counter[str]] = defaultdict(Counter)
    beginning_end_counts: dict[str, Counter[str]] = defaultdict(Counter)
    four_gram_counts: Counter[tuple[str, str, str, str]] = Counter()
    four_gram_a_counts: Counter[str] = Counter()
    four_gram_ab_counts: Counter[tuple[str, str]] = Counter()
    four_gram_abc_counts: Counter[tuple[str, str, str]] = Counter()

    for word in all_words:
        tokens = tokenize_word(word, vocab)

        beginning_next = get_beginning_bigram(tokens)
        if beginning_next:
            first, second = beginning_next
            beginning_next_counts[first][second] += 1

        beginning_end = get_beginning_end_bigram(tokens)
        if beginning_end:
            first, end = beginning_end
            beginning_end_counts[first][end] += 1

        middle_tokens = tokens[1:-1]
        for index in range(len(middle_tokens) - 3):
            four_gram = tuple(middle_tokens[index : index + 4])
            a, b, c, d = four_gram
            four_gram_counts[four_gram] += 1
            four_gram_a_counts[a] += 1
            four_gram_ab_counts[(a, b)] += 1
            four_gram_abc_counts[(a, b, c)] += 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    base_name = input_files[0].stem if args.input else "stdin"

    tokenizer_data = {
        "bos": BOS,
        "eos": EOS,
        "num_beginning_tokens": NUM_BEGINNING_TOKENS,
        "num_end_tokens": NUM_END_TOKENS,
        "num_middle_tokens": NUM_MIDDLE_TOKENS,
        "vocab": vocab,
        "id_to_token": {str(token_id): token for token, token_id in vocab.items()},
    }
    tokenizer_path = args.output_dir / f"{base_name}-tokenizer.json"
    tokenizer_path.write_text(json.dumps(tokenizer_data, indent=2), encoding="utf-8")

    vocab_items = sorted(vocab.items(), key=lambda item: item[1])
    token_order = [token for token, _ in vocab_items]
    token_rank = {token: index for index, token in enumerate(token_order)}
    beginning_tokens = [
        token
        for token, token_id in vocab_items
        if token_id < NUM_BEGINNING_TOKENS
    ]

    total_beginning_next = sum(
        sum(counter.values()) for counter in beginning_next_counts.values()
    )
    total_beginning_end = sum(
        sum(counter.values()) for counter in beginning_end_counts.values()
    )

    beginning_next_model = []
    for first in beginning_tokens:
        seconds = beginning_next_counts.get(first, Counter())
        first_total = sum(seconds.values())
        if total_beginning_next > 0:
            first_probability = first_total / total_beginning_next
        else:
            first_probability = 0.0
        ordered_seconds = [
            [
                second,
                count,
                (count / first_total) if first_total > 0 else 0.0,
            ]
            for second, count in sorted(
                seconds.items(),
                key=lambda item: (
                    -(item[1] / first_total) if first_total > 0 else 0.0,
                    token_rank.get(item[0], 10**9),
                ),
            )
        ]
        beginning_next_model.append([first, first_probability, ordered_seconds])
    beginning_next_model.sort(
        key=lambda item: (-item[1], token_rank.get(item[0], 10**9))
    )
    beginning_end_model = []
    for first in beginning_tokens:
        ends = beginning_end_counts.get(first, Counter())
        first_total = sum(ends.values())
        if total_beginning_end > 0:
            first_probability = first_total / total_beginning_end
        else:
            first_probability = 0.0
        ordered_ends = [
            [
                end,
                count,
                (count / first_total) if first_total > 0 else 0.0,
            ]
            for end, count in sorted(
                ends.items(),
                key=lambda item: (
                    -(item[1] / first_total) if first_total > 0 else 0.0,
                    token_rank.get(item[0], 10**9),
                ),
            )
        ]
        beginning_end_model.append([first, first_probability, ordered_ends])
    beginning_end_model.sort(
        key=lambda item: (-item[1], token_rank.get(item[0], 10**9))
    )

    total_four_grams = sum(four_gram_counts.values())
    four_gram_model: list[list[object]] = []
    for a, a_count in four_gram_a_counts.items():
        a_probability = (a_count / total_four_grams) if total_four_grams > 0 else 0.0
        b_entries: list[list[object]] = []
        for (ab_a, b), ab_count in four_gram_ab_counts.items():
            if ab_a != a:
                continue
            b_probability = (ab_count / a_count) if a_count > 0 else 0.0
            c_entries: list[list[object]] = []
            for (abc_a, abc_b, c), abc_count in four_gram_abc_counts.items():
                if abc_a != a or abc_b != b:
                    continue
                c_probability = (abc_count / ab_count) if ab_count > 0 else 0.0
                d_entries: list[list[object]] = []
                for (abcd_a, abcd_b, abcd_c, d), abcd_count in (
                    four_gram_counts.items()
                ):
                    if abcd_a != a or abcd_b != b or abcd_c != c:
                        continue
                    d_probability = (abcd_count / abc_count) if abc_count > 0 else 0.0
                    d_entries.append([d, abcd_count, d_probability])
                d_entries.sort(
                    key=lambda item: (-item[2], token_rank.get(item[0], 10**9))
                )
                if len(d_entries) >= 2:
                    c_entries.append([c, abc_count, c_probability, d_entries])
            c_entries.sort(
                key=lambda item: (-item[2], token_rank.get(item[0], 10**9))
            )
            if len(c_entries) >= 2:
                b_entries.append([b, ab_count, b_probability, c_entries])
        b_entries.sort(
            key=lambda item: (-item[2], token_rank.get(item[0], 10**9))
        )
        if len(b_entries) >= 2:
            four_gram_model.append([a, a_count, a_probability, b_entries])
    four_gram_model.sort(
        key=lambda item: (-item[2], token_rank.get(item[0], 10**9))
    )

    model_data = {
        "total_words": len(all_words),
        "beginning_next": beginning_next_model,
        "beginning_end": beginning_end_model,
        "four_gram": four_gram_model,
    }
    if len(beginning_next_model) != NUM_BEGINNING_TOKENS:
        print(
            "Error: beginning_next must include exactly "
            f"{NUM_BEGINNING_TOKENS} entries, got {len(beginning_next_model)}"
        )
        return 1
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
    print(f"Saved tokenizer to {tokenizer_path}")
    print(f"Saved model to {model_path}")


if __name__ == "__main__":
    main()
