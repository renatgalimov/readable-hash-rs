#!/usr/bin/env python3
"""Length-major phrase codec "lenmin v1": reference implementation and builder.

Experimental; alongside (not replacing) v1-v4 and dyn v1.

Model: an acyclic word automaton (states, accept flags, prefix-free choice
rows) and a word-count range. A phrase is k words (k in [kmin, kmax]) joined
by single spaces. Phrases are ordered by total length (letters + spaces),
then by word count k, then by length of word 1, word 1 rank, ... A u64 is the
position in that order; positions >= 2^64 are not valid phrases.
"""
import json
import math
import random
from bisect import bisect_right
from collections import Counter

HEADER = "lenmin v1"


def parse_text(text):
    lines = text.split("\n")
    assert lines[0] == HEADER, "header"
    name = lines[1].removeprefix("name ")
    parts = lines[2].removeprefix("words ").split()
    kmin, kmax = int(parts[0]), int(parts[-1])
    count = int(lines[3].removeprefix("states "))
    states = []
    for line in lines[4:4 + count]:
        flag, _, rest = line.partition("|")
        row = []
        for item in rest.split(" ") if rest else []:
            token, _, target = item.rpartition(">")
            row.append((token, int(target)))
        states.append((flag == "A", row))
    return name, kmin, kmax, states


def export_text(name, kmin, kmax, states):
    words = f"{kmin}" if kmin == kmax else f"{kmin} {kmax}"
    lines = [HEADER, f"name {name}", f"words {words}", f"states {len(states)}"]
    for accept, row in states:
        lines.append(("A|" if accept else "N|") + " ".join(f"{token}>{target}" for token, target in row))
    return "\n".join(lines) + "\n"


class LenMin:
    def __init__(self, kmin, kmax, states, limit=1 << 64):
        self.limit = limit
        self.kmin, self.kmax, self.states = kmin, kmax, states
        count = len(states)
        longest = [0] * count
        for index in range(count - 1, -1, -1):
            for token, target in states[index][1]:
                assert target > index
                longest[index] = max(longest[index], len(token) + longest[target])
        self.maxlen = longest[0]
        size = self.maxlen + 1
        self.count = [[0] * size for _ in range(count)]
        for index in range(count - 1, -1, -1):
            accept, row = states[index]
            table = self.count[index]
            if accept:
                table[0] = 1
            for token, target in row:
                width = len(token)
                child = self.count[target]
                for remaining in range(width, size):
                    table[remaining] += child[remaining - width]
        self.word_count = self.count[0]
        assert self.word_count[0] == 0
        # seq[k][t]: ordered k-word sequences with t letters in total
        self.seq = [[1]]
        for k in range(1, self.kmax + 1):
            previous = self.seq[-1]
            current = [0] * (k * self.maxlen + 1)
            for total in range(len(current)):
                current[total] = sum(self.word_count[w] * previous[total - w]
                                     for w in range(1, min(self.maxlen, total) + 1)
                                     if total - w < len(previous))
            self.seq.append(current)
        # classes[length] = [(k, letters, count)]
        by_length = {}
        for k in range(self.kmin, self.kmax + 1):
            for letters, value in enumerate(self.seq[k]):
                if value:
                    by_length.setdefault(letters + k - 1, []).append((k, letters, value))
        self.lengths = sorted(by_length)
        self.classes = [by_length[length] for length in self.lengths]
        self.class_total = [sum(entry[2] for entry in entries) for entries in self.classes]
        self.cumulative = [0]
        for value in self.class_total:
            self.cumulative.append(self.cumulative[-1] + value)
        self.capacity = self.cumulative[-1]
        if self.capacity < limit:
            raise ValueError(f"insufficient capacity log2={math.log2(self.capacity):.3f}")

    # ---------------------------------------------------------------- words
    def unrank_word(self, letters, rank):
        state, path, text = 0, [], ""
        remaining = letters
        while remaining:
            for token, target in self.states[state][1]:
                width = len(token)
                if width > remaining:
                    continue
                size = self.count[target][remaining - width]
                if rank < size:
                    break
                rank -= size
            else:
                raise AssertionError("rank out of range")
            path.append((state, token))
            text += token
            state, remaining = target, remaining - width
        assert rank == 0
        return text, path

    def parse_word(self, text):
        """-> (letters, rank, path) or None."""
        letters = len(text)
        if letters == 0 or letters > self.maxlen:
            return None
        state, rank, remaining, rest, path = 0, 0, letters, text, []
        while rest:
            for token, target in self.states[state][1]:
                if rest.startswith(token):
                    break
                width = len(token)
                if width <= remaining:
                    rank += self.count[target][remaining - width]
            else:
                return None
            path.append((state, token))
            rest, remaining, state = rest[len(token):], remaining - len(token), target
        if not self.states[state][0]:
            return None
        return letters, rank, path

    # -------------------------------------------------------------- phrases
    def encode(self, value, with_path=False):
        assert 0 <= value < self.limit
        index = bisect_right(self.cumulative, value) - 1
        value -= self.cumulative[index]
        for k, letters, count in self.classes[index]:
            if value < count:
                break
            value -= count
        words, paths, left = [], [], letters
        for position in range(k):
            tail = self.seq[k - position - 1]
            for length in range(1, self.maxlen + 1):
                if left - length < 0 or left - length >= len(tail):
                    continue
                block = self.word_count[length] * tail[left - length]
                if value < block:
                    break
                value -= block
            quotient, value = divmod(value, tail[left - length])
            text, path = self.unrank_word(length, quotient)
            words.append(text)
            paths.append(path)
            left -= length
        phrase = " ".join(words)
        return (phrase, paths) if with_path else phrase

    def decode(self, phrase):
        parts = phrase.split(" ")
        k = len(parts)
        if not self.kmin <= k <= self.kmax:
            return None
        parsed = [self.parse_word(part) for part in parts]
        if any(item is None for item in parsed):
            return None
        letters = sum(item[0] for item in parsed)
        length = letters + k - 1
        position = bisect_right(self.lengths, length) - 1
        if position < 0 or self.lengths[position] != length:
            return None
        value = self.cumulative[position]
        for entry in self.classes[position]:
            if entry[0] == k:
                break
            value += entry[2]
        left = letters
        for position, (word_letters, rank, _) in enumerate(parsed):
            tail = self.seq[k - position - 1]
            for shorter in range(1, word_letters):
                if left - shorter >= 0 and left - shorter < len(tail):
                    value += self.word_count[shorter] * tail[left - shorter]
            value += rank * tail[left - word_letters]
            left -= word_letters
        return value if value < self.limit else None

    # ------------------------------------------------------------ statistics
    def reachable_length_histogram(self):
        """Exact {total length: number of u64 values} for values 0..2^64-1."""
        histogram, remaining = {}, self.limit
        for length, total in zip(self.lengths, self.class_total):
            take = min(total, remaining)
            histogram[length] = take
            remaining -= take
            if not remaining:
                break
        return histogram

    def length_stats(self):
        histogram = self.reachable_length_histogram()
        total = self.limit
        mean = sum(length * count for length, count in histogram.items()) / total
        return {
            "mean": mean, "min": min(histogram), "max": max(histogram),
            "median": next(length for length, _ in self._cum(histogram) if _ >= total / 2),
            "p99": next(length for length, cum in self._cum(histogram) if cum >= total * 0.99),
            "histogram": {str(length): count / total for length, count in sorted(histogram.items())},
        }

    @staticmethod
    def _cum(histogram):
        running = 0
        for length in sorted(histogram):
            running += histogram[length]
            yield length, running

    def log2_capacity(self):
        return math.log2(self.capacity)


def mix(value):
    mask = (1 << 64) - 1
    value ^= value >> 30
    value = (value * 0xBF58476D1CE4E5B9) & mask
    value ^= value >> 27
    value = (value * 0x94D049BB133111EB) & mask
    return value ^ (value >> 31)


def lcg_values(count, seed=0x9E3779B97F4A7C15):
    state, mask = seed, (1 << 64) - 1
    for _ in range(count):
        state = (state * 6364136223846793005 + 1442695040888963407) & mask
        yield state
