#!/usr/bin/env python3
"""Test tokenizer by converting words into token streams."""

import argparse
import json
from pathlib import Path

BOS = "^"
EOS = "$"


def tokenize_word(word: str, vocab: dict[str, int]) -> list[str]:
    """Tokenize a word using greedy longest-match with position awareness."""
    if len(word) == 0:
        return []

    tokens = []
    position = 0

    while position < len(word):
        is_beginning = position == 0

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
            elif position == len(word) - 1:
                best_token = f"{word[position]}{EOS}"
            else:
                best_token = word[position]
            best_length = 1

        tokens.append(best_token)
        position += best_length

    return tokens


def main():
    parser = argparse.ArgumentParser(description="Test tokenizer on words")
    parser.add_argument(
        "words",
        nargs="+",
        help="Words to tokenize",
    )
    parser.add_argument(
        "-t",
        "--tokenizer",
        type=Path,
        default=Path("training-data/english-lowercase-tokenizer.json"),
        help="Tokenizer file (default: training-data/english-lowercase-tokenizer.json)",
    )
    parser.add_argument(
        "--ids",
        action="store_true",
        help="Show token IDs instead of tokens",
    )
    args = parser.parse_args()

    if not args.tokenizer.exists():
        print(f"Error: Tokenizer file {args.tokenizer} does not exist")
        return 1

    tokenizer_data = json.loads(args.tokenizer.read_text(encoding="utf-8"))
    vocab = tokenizer_data["vocab"]

    for word in args.words:
        word_lower = word.lower()
        tokens = tokenize_word(word_lower, vocab)

        if args.ids:
            token_ids = [vocab.get(token, -1) for token in tokens]
            print(f"{word}: {token_ids}")
        else:
            print(f"{word}: {tokens}")


if __name__ == "__main__":
    main()
