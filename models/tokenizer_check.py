#!/usr/bin/env python3
"""Load a trained tokenizer and encode sample text."""

import argparse
from tokenizers import Tokenizer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tokenizer", help="Path to tokenizer.json")
    parser.add_argument("text", help="Text to encode")
    args = parser.parse_args()

    tokenizer = Tokenizer.from_file(args.tokenizer)
    encoding = tokenizer.encode(args.text)
    print(encoding.ids)


if __name__ == "__main__":
    main()
