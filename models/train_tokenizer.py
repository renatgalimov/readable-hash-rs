#!/usr/bin/env python3
"""Train a Byte-Level BPE tokenizer using HuggingFace tokenizers.

This script expects one or more plain text files that will be used to
train a tokenizer. The resulting vocabulary, merges and ``tokenizer.json``
are written to an output directory (default: ``tokenizer``).

Example usage:
    python train_tokenizer.py data.txt --output-dir my_tokenizer
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from tokenizers import ByteLevelBPETokenizer

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "tokenizer"


DEFAULT_SPECIAL_TOKENS = [
    "<s>",
    "<pad>",
    "</s>",
    "<unk>",
    "<mask>",
]


def train_tokenizer(
    files: Iterable[str],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    vocab_size: int = 30522,
    min_frequency: int = 2,
    special_tokens: Iterable[str] | None = None,
) -> None:
    """Train and save a Byte-Level BPE tokenizer."""
    tokenizer = ByteLevelBPETokenizer()
    tokenizer.train(
        files=list(files),
        vocab_size=vocab_size,
        min_frequency=min_frequency,
        special_tokens=list(special_tokens or DEFAULT_SPECIAL_TOKENS),
    )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tokenizer.save_model(str(out_dir))
    tokenizer.save(str(out_dir / "tokenizer.json"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", help="Training text files")
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Where to write the tokenizer files",
    )
    parser.add_argument("--vocab-size", type=int, default=30522)
    parser.add_argument("--min-frequency", type=int, default=2)
    args = parser.parse_args()

    train_tokenizer(
        args.files,
        output_dir=args.output_dir,
        vocab_size=args.vocab_size,
        min_frequency=args.min_frequency,
    )
