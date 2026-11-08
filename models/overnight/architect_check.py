#!/usr/bin/env python3
"""Numerical check of the architect's idealised token-count analysis.

Idealised grammar: B=128 beginnings, C=64 continuations, a word is B C^(n-1)
with n in 1..4 tokens, exactly 3 words, spaces free (word ends anywhere).
Phrases ordered by total token count (a proxy for length); 1-token words are
treated as ordinary B tokens here (the real codec restricts them to a curated
list, which is quantified separately)."""
import json
import math
from fractions import Fraction


def analysis(begin=128, cont=64, words=3, max_tokens=4):
    word = {n: begin * cont ** (n - 1) for n in range(1, max_tokens + 1)}
    seq = {0: {0: 1}}
    for k in range(1, words + 1):
        seq[k] = {}
        for total, count in seq[k - 1].items():
            for n, ways in word.items():
                seq[k][total + n] = seq[k].get(total + n, 0) + count * ways
    classes = sorted(seq[words].items())
    remaining, histogram = 1 << 64, {}
    for tokens, count in classes:
        take = min(count, remaining)
        histogram[tokens] = take
        remaining -= take
        if not remaining:
            break
    mean = sum(tokens * count for tokens, count in histogram.items()) / (1 << 64)
    layouts = {}
    for tokens in range(words, words * max_tokens + 1):
        layouts[tokens] = sum(1 for a in range(1, max_tokens + 1) for b in range(1, max_tokens + 1)
                              for c in range(1, max_tokens + 1) if a + b + c == tokens) if words == 3 else None
    return {
        "begin": begin, "cont": cont, "words": words, "max_tokens": max_tokens,
        "mean_tokens_length_major": mean, "max_tokens_used": max(histogram),
        "log2_total_capacity": math.log2(sum(count for _, count in classes)),
        "layouts_of_10_tokens": layouts.get(10),
        "bits_fixed_layout_10_tokens": math.log2(begin ** 3 * cont ** 7),
        "bits_all_10_token_layouts": math.log2(layouts.get(10, 1) * begin ** 3 * cont ** 7) if layouts.get(10) else None,
        "fixed_4_4_4_tokens_bits": math.log2(begin ** 3 * cont ** 9),
        "fixed_3_4_4_tokens_bits": math.log2(begin ** 3 * cont ** 8),
        "histogram_tokens": {str(k): v / (1 << 64) for k, v in histogram.items()},
    }


if __name__ == "__main__":
    print(json.dumps([analysis(), analysis(128, 64, 3, 5), analysis(256, 64, 3, 4)], indent=1))
