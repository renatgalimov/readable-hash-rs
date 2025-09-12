#!/usr/bin/env python3
"""Train an n-gram language model using a pre-trained tokenizer.

This script reads one or more text files, tokenizes the contents with a
provided tokenizer, and computes n-gram transition probabilities between
tokens. The resulting model is written as JSON where each key is a
space-delimited sequence of ``n-1`` token ids mapping to a dictionary of
successor token ids and their probabilities.

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

    The model estimates transition probabilities between token ids produced by
    the tokenizer. The tokenizer **must** define start (``<s>``) and end
    (``</s>``) tokens; each input line is wrapped with ``n-1`` start tokens and
    a single end token before collecting statistics. Token sequences are
    validated so that continuation tokens (prefixed with ``##``) only follow
    tokens that do not end a word (those lacking the ``</w>`` suffix).
    """

    if n < 1:
        raise ValueError("n must be at least 1")

    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    start_id = tokenizer.token_to_id("<s>")
    end_id = tokenizer.token_to_id("</s>")
    if start_id is None or end_id is None:
        raise ValueError("Tokenizer must include <s> and </s> tokens")

    counts: dict[Tuple[int, ...], Counter[int]] = defaultdict(Counter)
    totals: Counter[Tuple[int, ...]] = Counter()

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

                tokens = [start_id] * (n - 1) + token_ids + [end_id]
                for i in range(len(tokens) - n + 1):
                    context = tuple(tokens[i : i + n - 1])
                    next_id = tokens[i + n - 1]
                    counts[context][next_id] += 1
                    totals[context] += 1

    model = {
        " ".join(map(str, context)): {
            str(next_id): count / totals[context]
            for next_id, count in successor_counts.items()
        }
        for context, successor_counts in counts.items()
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
