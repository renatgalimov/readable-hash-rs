#!/usr/bin/env python3
"""Train a BPE tokenizer with explicit word boundary markers."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from tokenizers import Tokenizer
from tokenizers.models import BPE
from tokenizers.normalizers import Lowercase, NFKC, Sequence
from tokenizers.pre_tokenizers import Whitespace
from tokenizers.trainers import BpeTrainer

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
    """Train and save a Byte-Level BPE tokenizer with word boundaries.

    The input text is normalized using Unicode NFKC and lowercased before
    training to ensure consistent results. Tokens that continue a word are
    prefixed with ``##`` while tokens that end a word receive a ``</w>``
    suffix. A token without the prefix starts a word, and the presence of the
    suffix marks that the word ends at that token.
    """
    model = BPE(
        continuing_subword_prefix="##",
        end_of_word_suffix="</w>",
    )
    tokenizer = Tokenizer(model)
    tokenizer.normalizer = Sequence([NFKC(), Lowercase()])
    tokenizer.pre_tokenizer = Whitespace()

    trainer = BpeTrainer(
        vocab_size=vocab_size,
        min_frequency=min_frequency,
        special_tokens=list(special_tokens or DEFAULT_SPECIAL_TOKENS),
        continuing_subword_prefix="##",
        end_of_word_suffix="</w>",
    )
    tokenizer.train(list(files), trainer)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tokenizer.model.save(str(out_dir))
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

