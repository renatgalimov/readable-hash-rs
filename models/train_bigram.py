#!/usr/bin/env python3
"""Train a bigram language model using a pre-trained tokenizer.

This script reads one or more text files, tokenizes the contents with a
provided tokenizer, and computes bigram transition probabilities between
tokens. The resulting model is written as JSON where each key is a token id
mapping to a dictionary of successor token ids and their probabilities.

Example usage:
    python train_bigram.py sample_corpus.txt
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from tokenizers import Tokenizer

DEFAULT_TOKENIZER_PATH = (
    Path(__file__).resolve().parent / "tokenizer" / "tokenizer.json"
)
DEFAULT_OUTPUT_FILE = Path(__file__).resolve().parent / "bigram.json"


def train_bigram(
    input_files: Iterable[str],
    tokenizer_path: str | Path = DEFAULT_TOKENIZER_PATH,
    output_file: str | Path = DEFAULT_OUTPUT_FILE,
) -> None:
    """Train and save a bigram language model.

    The model estimates transition probabilities between token ids produced by
    the tokenizer. The tokenizer **must** define start (``<s>``) and end
    (``</s>``) tokens; each input line is wrapped with these tokens before
    collecting bigram statistics. Token sequences are validated so that
    continuation tokens (prefixed with ``##``) only follow tokens that do not
    end a word (those lacking the ``</w>`` suffix).
    """

    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    start_id = tokenizer.token_to_id("<s>")
    end_id = tokenizer.token_to_id("</s>")
    if start_id is None or end_id is None:
        raise ValueError("Tokenizer must include <s> and </s> tokens")

    counts: dict[int, Counter[int]] = defaultdict(Counter)
    totals: Counter[int] = Counter()

    for file_path in input_files:
        with open(file_path, "r", encoding="utf-8") as file_handle:
            for line in file_handle:
                encoding = tokenizer.encode(line, add_special_tokens=False)
                token_ids = encoding.ids
                token_strs = encoding.tokens
                if not token_ids:
                    continue

                prev = "<s>"
                for tok in token_strs:
                    if tok.startswith("##"):
                        if prev == "<s>" or prev.endswith("</w>"):
                            raise ValueError(f"Token {tok!r} cannot start a word")
                    else:
                        if prev != "<s>" and not prev.endswith("</w>"):
                            raise ValueError(f"Token {tok!r} must be a continuation")
                    prev = tok

                tokens = [start_id] + token_ids + [end_id]
                for current_id, next_id in zip(tokens, tokens[1:]):
                    counts[current_id][next_id] += 1
                    totals[current_id] += 1

    model = {
        str(current_id): {
            str(next_id): count / totals[current_id]
            for next_id, count in successor_counts.items()
        }
        for current_id, successor_counts in counts.items()
    }

    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as output_handle:
        json.dump(model, output_handle)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "files", nargs="+", help="Training text files"
    )
    parser.add_argument(
        "--tokenizer",
        default=DEFAULT_TOKENIZER_PATH,
        help="Path to tokenizer.json",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_FILE,
        help="Where to write the bigram model JSON",
    )
    args = parser.parse_args()

    train_bigram(args.files, args.tokenizer, args.output)
