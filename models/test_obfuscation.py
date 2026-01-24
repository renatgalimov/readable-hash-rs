#!/usr/bin/env python3
"""Test obfuscation by converting numbers to tokens using the trigram model."""

import argparse
import json
import math
from pathlib import Path


def bits_needed(options: int) -> int:
    """Calculate bits needed to represent n options."""
    if options <= 1:
        return 0
    return math.ceil(math.log2(options))


def main():
    parser = argparse.ArgumentParser(
        description="Convert a number to tokens using the tokenizer"
    )
    parser.add_argument(
        "number",
        type=int,
        help="Number to convert",
    )
    parser.add_argument(
        "-t",
        "--tokenizer",
        type=Path,
        default=Path("training-data/english-lowercase-tokenizer.json"),
        help="Tokenizer file",
    )
    parser.add_argument(
        "-m",
        "--model",
        type=Path,
        default=Path("training-data/english-lowercase-model.json"),
        help="Model file",
    )
    args = parser.parse_args()

    if not args.tokenizer.exists():
        print(f"Error: Tokenizer file {args.tokenizer} does not exist")
        return 1

    if not args.model.exists():
        print(f"Error: Model file {args.model} does not exist")
        return 1

    tokenizer_data = json.loads(args.tokenizer.read_text(encoding="utf-8"))
    id_to_token = tokenizer_data["id_to_token"]

    model_data = json.loads(args.model.read_text(encoding="utf-8"))
    model = model_data["model"]

    number = args.number
    first_byte = number & 0xFF
    remaining = number >> 8

    token = id_to_token.get(str(first_byte), f"[UNK:{first_byte}]")
    second_level_options = len(model.get(token, {}))
    bits_for_next = bits_needed(second_level_options)

    extract_bits = bits_for_next - 1
    if extract_bits > 0:
        mask = (1 << extract_bits) - 1
        extracted = remaining & mask
        remaining = remaining >> extract_bits
    else:
        extracted = 0

    remaining_binary = bin(remaining)[2:] if remaining > 0 else "0"

    print(f"{token} ({bits_for_next} bits) {extracted} {remaining_binary}")


if __name__ == "__main__":
    main()
