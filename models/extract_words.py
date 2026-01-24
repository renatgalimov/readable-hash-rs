#!/usr/bin/env python3
"""Extract unique lowercase words from text files for tokenizer training."""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path


def extract_lowercase_words(text: str) -> list[str]:
    """Extract lowercase alphabetic words from text."""
    return re.findall(r"[a-z]+", text.lower())


def check_language(filepath: Path, language: str) -> bool:
    """Check if file matches the specified language by scanning first 30 lines."""
    if language == "english":
        with filepath.open(encoding="utf-8", errors="ignore") as file:
            for line_number, line in enumerate(file):
                if line_number >= 30:
                    break
                if "Language: English" in line:
                    return True
        return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Extract unique lowercase words from text files"
    )
    parser.add_argument(
        "input",
        nargs="*",
        type=Path,
        help="Input text files (reads from stdin if none provided)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("training-data/english-lowercase.txt"),
        help="Output file (default: training-data/english-lowercase.txt)",
    )
    parser.add_argument(
        "-l",
        "--language",
        type=str,
        default="english",
        help="Language to filter for (default: english)",
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="Include word counts in output",
    )
    parser.add_argument(
        "--min-frequency",
        type=int,
        default=2,
        help="Minimum occurrences required to keep a word (default: 2)",
    )
    parser.add_argument(
        "--min-length",
        type=int,
        default=2,
        help="Minimum character length required to keep a word (default: 2)",
    )
    args = parser.parse_args()

    word_counts: Counter[str] = Counter()

    def process_file(filepath: Path) -> None:
        if not check_language(filepath, args.language.lower()):
            print(f"Skipping {filepath} (language mismatch)")
            return
        text = filepath.read_text(encoding="utf-8", errors="ignore")
        word_counts.update(extract_lowercase_words(text))

    if args.input:
        for filepath in args.input:
            if filepath.is_file():
                process_file(filepath)
            elif filepath.is_dir():
                for txt_file in filepath.glob("**/*.txt"):
                    if txt_file != args.output:
                        process_file(txt_file)
    else:
        text = sys.stdin.read()
        word_counts.update(extract_lowercase_words(text))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    minimum_frequency = max(args.min_frequency, 1)
    minimum_length = max(args.min_length, 1)
    filtered_words = [
        word
        for word in word_counts
        if len(word) >= minimum_length and word_counts[word] >= minimum_frequency
    ]
    sorted_words = sorted(filtered_words, key=len)
    if args.count:
        lines = [f"{word}\t{word_counts[word]}" for word in sorted_words]
    else:
        lines = sorted_words
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Extracted {len(sorted_words)} unique lowercase words to {args.output}")


if __name__ == "__main__":
    main()
