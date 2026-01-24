#!/usr/bin/env python3
"""Train an n-gram language model using a pre-trained tokenizer.

This script reads one or more text files, tokenizes the contents with a
provided tokenizer, and computes n-gram successor frequencies between
tokens. The resulting model is written as a JSON list where each element
contains a predecessor token sequence of length ``n-1`` and a list of
successor tokens ordered by frequency.

Example usage:
    python train_ngram.py sample_corpus.txt -n 3
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Tuple

from tokenizers import Tokenizer

DEFAULT_TOKENIZER_PATH = (
    Path(__file__).resolve().parent / "tokenizer" / "tokenizer.json"
)
DEFAULT_OUTPUT_FILE = Path(__file__).resolve().parent / "ngram.json"


def train_ngram(
    input_files: Iterable[str],
    n: int,
    tokenizer_path: str | Path = DEFAULT_TOKENIZER_PATH,
    output_file: str | Path = DEFAULT_OUTPUT_FILE,
) -> None:
    """Train and save an n-gram language model.

    The model records successor token frequencies rather than probabilities.
    The tokenizer **must** define start (``<s>``) and end (``</s>``) tokens;
    each input line is wrapped with ``n-1`` start tokens and a single end
    token before collecting statistics. Token sequences are validated so that
    continuation tokens (prefixed with ``##``) only follow tokens that do not
    end a word (those lacking the ``</w>`` suffix).
    """

    if n < 1:
        raise ValueError("n must be at least 1")

    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    if tokenizer.token_to_id("<s>") is None or tokenizer.token_to_id("</s>") is None:
        raise ValueError("Tokenizer must include <s> and </s> tokens")

    counts: dict[Tuple[str, ...], Counter[str]] = defaultdict(Counter)

    for file_path in input_files:
        with open(file_path, "r", encoding="utf-8") as file_handle:
            for line in file_handle:
                encoding = tokenizer.encode(line, add_special_tokens=False)
                token_strs = encoding.tokens
                if not token_strs:
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

                tokens = ["<s>"] * (n - 1) + token_strs + ["</s>"]
                for i in range(len(tokens) - n + 1):
                    context = tuple(tokens[i : i + n - 1])
                    next_token = tokens[i + n - 1]
                    counts[context][next_token] += 1

    model: list[list[list[str], list[str]]] = []
    for context, successor_counts in counts.items():
        sorted_successors = [tok for tok, _ in successor_counts.most_common()]
        model.append([list(context), sorted_successors])

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
        "-n",
        type=int,
        default=2,
        help="Order of the n-gram model",
    )
    parser.add_argument(
        "--tokenizer",
        default=DEFAULT_TOKENIZER_PATH,
        help="Path to tokenizer.json",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_FILE,
        help="Where to write the n-gram model JSON",
    )
    args = parser.parse_args()

    train_ngram(args.files, args.n, args.tokenizer, args.output)
