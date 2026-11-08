#!/usr/bin/env python3
"""Can a v5 word (beginning, 0-3 middles, ending) be read two ways with v3's context tables?

v3 always has 4 tokens per word, so its decoder knows where the ending is. v5 words have 2-5
tokens, so the decoder must find the ending from the letters alone. This searches, for every
beginning and both ending tables (END32 and v4's END16), for two different token paths that spell
the same word. It walks both paths in step (a product automaton) instead of listing every word.
"""
import json
from collections import Counter, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAX_MIDDLES = 3


def context(token):
    return token if token < 256 else token - 256


def load():
    model = json.loads((ROOT / "phrase_v3_model.json").read_text())
    end16 = json.loads((ROOT / "phrase_v4_end16.json").read_text())["end16"]
    text = [token.strip("^$") for token in model["tokens"]]
    return model, end16, text


def find_ambiguities(begin_token, middle_rows, end_rows, text):
    """Return (middles_a, middles_b, spelling_a, spelling_b) for every pair of paths that read the same."""
    start = (context(begin_token), 0)

    def moves(state):
        ctx, middles = state
        if middles < MAX_MIDDLES:
            for token in middle_rows[ctx]:
                yield token, "m", (context(token), middles + 1)
        for token in end_rows[ctx]:
            yield token, "e", ("done", middles)

    found = []
    # Node: (state_a, state_b, surplus text, which side is ahead, diverged, path_a, path_b)
    queue: deque = deque([(start, start, "", None, False, (), ())])
    seen = set()
    while queue:
        a, b, surplus, ahead, diverged, path_a, path_b = queue.popleft()
        key = (a, b, surplus, ahead, diverged)
        if key in seen:
            continue
        seen.add(key)
        if surplus == "" and a[0] == "done" and b[0] == "done":
            if diverged:
                found.append((a[1], b[1], path_a, path_b))
            continue
        if surplus == "":
            if a[0] == "done" or b[0] == "done":
                continue  # one word ended, the other still needs letters
            for token_a, kind_a, next_a in moves(a):
                for token_b, kind_b, next_b in moves(b):
                    ta, tb = text[token_a], text[token_b]
                    if (token_a, kind_a) == (token_b, kind_b):
                        continue  # identical step: covered by the state it leads to (searched from start)
                    if ta.startswith(tb):
                        queue.append((next_a, next_b, ta[len(tb):], "a" if ta != tb else None, True,
                                      path_a + (ta,), path_b + (tb,)))
                    elif tb.startswith(ta):
                        queue.append((next_a, next_b, tb[len(ta):], "b", True, path_a + (ta,), path_b + (tb,)))
            # identical steps: continue both paths together
            for token, kind, nxt in moves(a):
                if nxt[0] != "done":
                    queue.append((nxt, nxt, "", None, False, path_a + (text[token],), path_b + (text[token],)))
            continue
        behind = b if ahead == "a" else a
        if behind[0] == "done":
            continue
        for token, kind, nxt in moves(behind):
            t = text[token]
            if surplus.startswith(t):
                rest, new_ahead = surplus[len(t):], ahead
            elif t.startswith(surplus):
                rest, new_ahead = t[len(surplus):], ("b" if ahead == "a" else "a")
            else:
                continue
            if rest == "":
                new_ahead = None
            if ahead == "a":
                queue.append((a, nxt, rest, new_ahead, True, path_a, path_b + (t,)))
            else:
                queue.append((nxt, b, rest, new_ahead, True, path_a + (t,), path_b))
    return found


def main():
    model, end16, text = load()
    report = {}
    for name, end_rows in (("end32", model["end32"]), ("end16", end16)):
        lengths = Counter()
        examples = []
        begins_hit = 0
        for begin in model["begin"]:
            found = find_ambiguities(begin, model["middle32"], end_rows, text)
            if found:
                begins_hit += 1
            for middles_a, middles_b, path_a, path_b in found:
                lengths[tuple(sorted((middles_a + 2, middles_b + 2)))] += 1
                if len(examples) < 8:
                    examples.append((text[begin], "+".join(path_a), "+".join(path_b)))
        report[name] = {"begins_with_ambiguity": begins_hit, "pairs_by_token_counts": dict(lengths), "examples": examples}
        print(name, "beginnings with an ambiguous word:", begins_hit, "of", len(model["begin"]))
        print("  ambiguous pairs by (tokens, tokens):", dict(sorted(lengths.items())))
        for begin, path_a, path_b in examples:
            print(f"  {begin}+{path_a}  ==  {begin}+{path_b}")
    return report


if __name__ == "__main__":
    main()
