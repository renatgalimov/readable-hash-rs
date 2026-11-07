#!/usr/bin/env python3
"""Exact word-length extrema over all paths and over the u64 domain."""
import json
from compile_reversible import DATA, compile_tables


def lengths(beginning, rows, tokens, bounded, maximum=(1 << 64) - 1):
    def token_length(token):
        return len(tokens[token].removeprefix('^').removesuffix('$'))

    def context(token):
        return token if token < 256 else token - 256

    # Process least-significant digits first. The comparison state is overwritten
    # by each unequal higher digit, so it describes the processed integer.
    states = {}
    for index, token in enumerate(beginning):
        bound = (maximum - index) // len(beginning) if bounded else (1 << 59) - 1
        key = (bound, token, 0)
        size = token_length(token)
        old = states.get(key, (size, size))
        states[key] = (min(size, old[0]), max(size, old[1]))
    for position in range(11):
        following = {}
        for (bound, token, comparison), (minimum, maximum) in states.items():
            bound_digit = (bound >> (5 * position)) & 31
            for digit, next_token in enumerate(rows['middle'][context(token)]):
                next_comparison = (digit > bound_digit) - (digit < bound_digit) or comparison
                key = (bound, next_token, next_comparison)
                size = token_length(next_token)
                low, high = following.get(key, (minimum + size, maximum + size))
                following[key] = (min(low, minimum + size), max(high, maximum + size))
        states = following
    extrema = []
    for (bound, token, comparison), (minimum, maximum) in states.items():
        bound_digit = bound >> 55
        for digit, end_token in enumerate(rows['end'][context(token)]):
            relation = (digit > bound_digit) - (digit < bound_digit) or comparison
            if relation <= 0:
                size = token_length(end_token)
                extrema.append((minimum + size, maximum + size))
    return min(pair[0] for pair in extrema), max(pair[1] for pair in extrema)


def main():
    beginning, rows, _, _, _ = compile_tables()
    tokens = json.loads((DATA / 'english-lowercase-model.json').read_text())['id_to_token']
    print('all syntactic paths:', lengths(beginning, rows, tokens, False))
    print('valid u64 paths:', lengths(beginning, rows, tokens, True))


if __name__ == '__main__':
    main()
