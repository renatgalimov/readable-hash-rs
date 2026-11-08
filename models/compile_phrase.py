#!/usr/bin/env python3
"""Compile experimental 22+21+21-bit phrase tables; v1 is untouched."""
import argparse
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path

from reversible_tables import choose_prefix_free, load_training_counts

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "training-data"
MODEL_PATH = ROOT / "phrase_model.json"
REPORT_PATH = ROOT / "phrase_report.json"
RUST_PATH = ROOT.parent / "src" / "phrase_v2_data.rs"
CONTEXTS = list(range(256)) + list(range(512, 1024))


def emitted(token):
    return token.removeprefix("^").removesuffix("$")


def valid(text):
    return bool(text) and text.isascii() and text.isalpha() and text.islower()


def prefix_free(texts):
    ordered = sorted(texts)
    return len(ordered) == len(set(ordered)) and all(
        not right.startswith(left) for left, right in zip(ordered, ordered[1:])
    )


def compile_model(revised=False):
    source = json.loads((DATA / "english-lowercase-model.json").read_text())
    tokens = source["id_to_token"]
    counts = load_training_counts(DATA / "english-lowercase.txt", DATA / "english-lowercase-model.json")
    pools = {
        "middle": {tokens[index]: index for index in range(512, 1024) if valid(tokens[index])},
        "end": {emitted(tokens[index]): index for index in range(256, 512) if tokens[index].endswith("$") and valid(emitted(tokens[index]))},
    }
    rows = {}
    omissions = {}
    local_slots = {}
    specifications = (("middle32", 32), ("middle16", 16), ("end32", 32)) if revised else (("middle16", 16), ("middle8", 8), ("end128", 128))
    first_label, second_label, end_label = (label for label, _ in specifications)
    for label, size in specifications:
        kind = "end" if label.startswith("end") else "middle"
        pool = pools[kind]
        global_counts = sum(counts[kind].values(), Counter())
        rows[label], omissions[label], local_slots[label] = [], {}, []
        cache = {}
        for context in CONTEXTS:
            local = counts[kind].get(context, Counter())
            key = tuple(sorted(local.items()))
            if key not in cache:
                candidates = {text: (local.get(index, 0), global_counts[index] if not local.get(index, 0) else 0) for text, index in pool.items()}
                choices = choose_prefix_free(candidates, size)
                cache[key] = [pool[text] for text in choices]
            row = cache[key]
            rows[label].append(row)
            selected = set(row)
            missing = [tokens[index] for index in sorted(local) if index not in selected]
            if missing:
                omissions[label][str(context)] = missing
            local_slots[label].append(sum(index in local for index in row))
    context_index = {context: index for index, context in enumerate(CONTEXTS)}
    beginning = {emitted(tokens[index]): index for index in range(256) if tokens[index].startswith("^") and valid(emitted(tokens[index]))}
    for index in counts["begin"]:
        text = emitted(tokens[index])
        if valid(text):
            beginning.setdefault(text, index)
    # Count distinct observed, selected B->M->M->E paths, not raw IDs or
    # transition frequencies. Each selected row is already prefix-free.
    def connectivity(index):
        first_row = rows[first_label][context_index[index]]
        observed_first = counts["middle"].get(index, {})
        return sum(
            local_slots[end_label][context_index[second]]
            for first in first_row if first in observed_first
            for second in rows[first_label][context_index[first]]
            if second in counts["middle"].get(first, {})
        )
    candidates = {text: (connectivity(index), counts["begin"][index]) for text, index in beginning.items()}
    begin = [beginning[text] for text in choose_prefix_free(candidates, 128)]
    model = {"version": "experimental-phrase-3" if revised else "experimental-phrase-1", "tokens": tokens, "contexts": CONTEXTS,
             "begin": begin, **rows}
    validate(model)
    stats = statistics(model, counts, local_slots)
    stats["beginning_omitted_local"] = [tokens[index] for index in sorted(counts["begin"]) if index not in set(begin)]
    report = {"statistics": stats, "omitted_local_tokens_by_context_id": omissions}
    return model, report


def validate(model):
    tokens, contexts = model["tokens"], model["contexts"]
    assert contexts == CONTEXTS
    assert len(model["begin"]) == 128 and prefix_free([emitted(tokens[index]) for index in model["begin"]])
    assert all(index in contexts for index in model["begin"])
    specs = (("middle32", 32), ("middle16", 16), ("end32", 32)) if "middle32" in model else (("middle16", 16), ("middle8", 8), ("end128", 128))
    for label, size in specs:
        allowed = range(256, 512) if label.startswith("end") else range(512, 1024)
        assert len(model[label]) == len(contexts)
        for row in model[label]:
            assert len(row) == size and all(index in allowed for index in row)
            assert all(valid(emitted(tokens[index])) for index in row)
            assert prefix_free([emitted(tokens[index]) for index in row])


def statistics(model, counts, local_slots):
    tokens = model["tokens"]
    context_index = {context: index for index, context in enumerate(CONTEXTS)}
    length = lambda index: len(emitted(tokens[index]))
    # State values are exact min, max, sum of lengths and number of paths.
    def word_stats(second):
        states = {index: (length(index), length(index), length(index), 1) for index in model["begin"]}
        coverage = {}
        first_label = "middle32" if "middle32" in model else "middle16"
        end_label = "end32" if "middle32" in model else "end128"
        for position, label in enumerate((first_label, second, end_label), start=1):
            next_states = {}
            local_path_count = 0
            all_path_count = 0
            for context, (minimum, maximum, total, paths) in states.items():
                row = model[label][context_index[context]]
                observed = counts["end" if label.startswith("end") else "middle"].get(context, {})
                local_path_count += paths * sum(index in observed for index in row)
                all_path_count += paths * len(row)
                for index in row:
                    token_length = length(index)
                    old = next_states.get(index)
                    value = (minimum + token_length, maximum + token_length, total + paths * token_length, paths)
                    if old:
                        value = (min(old[0], value[0]), max(old[1], value[1]), old[2] + value[2], old[3] + paths)
                    next_states[index] = value
            coverage[f"{position}_{label}"] = {"local_paths": local_path_count, "all_paths": all_path_count, "local_fraction": float(Fraction(local_path_count, all_path_count))}
            states = next_states
        total = sum(value[2] for value in states.values())
        paths = sum(value[3] for value in states.values())
        return {"min_letters": min(value[0] for value in states.values()), "max_letters": max(value[1] for value in states.values()), "mean_letters": float(Fraction(total, paths)), "paths": paths, "coverage": coverage}
    first = word_stats("middle32" if "middle32" in model else "middle16")
    other = word_stats("middle16" if "middle32" in model else "middle8")
    return {"corpus_words": counts["word_count"], "word1": first, "word2_and_3": other,
            "phrase_min_letters": first["min_letters"] + 2 * other["min_letters"],
            "phrase_max_letters": first["max_letters"] + 2 * other["max_letters"],
            "phrase_mean_letters": first["mean_letters"] + 2 * other["mean_letters"],
            "spaces": 2,
            "row_local_slot_summary": {label: {"min": min(values), "max": max(values), "sum": sum(values), "slots": len(values) * len(model[label][0])} for label, values in local_slots.items()}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--v3", action="store_true")
    args = parser.parse_args()
    model, report = compile_model(args.v3)
    model_path = ROOT / "phrase_v3_model.json" if args.v3 else MODEL_PATH
    report_path = ROOT / "phrase_v3_report.json" if args.v3 else REPORT_PATH
    rust_path = ROOT.parent / "src" / "phrase_v3_data.rs" if args.v3 else RUST_PATH
    for path, data in ((model_path, model), (report_path, report)):
        output = json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n"
        if args.check:
            if path.read_text() != output:
                raise SystemExit(f"generated file differs: {path}")
        else:
            path.write_text(output)
    rust = '// Generated by models/compile_phrase.py; do not edit.\n'
    rust += '#![allow(clippy::unreadable_literal)]\n'
    rust += '#[rustfmt::skip]\npub static TOKENS: [&str; 1024] = ' + json.dumps(model['tokens'], ensure_ascii=True) + ';\n'
    rust += '#[rustfmt::skip]\npub static BEGIN: [u16; 128] = ' + json.dumps(model['begin']) + ';\n'
    specs = (("middle32", 32), ("middle16", 16), ("end32", 32)) if args.v3 else (("middle16", 16), ("middle8", 8), ("end128", 128))
    for key, size in specs:
        rust += f'#[rustfmt::skip]\npub static {key.upper()}: [[u16; {size}]; 768] = ' + json.dumps(model[key]) + ';\n'
    if args.check:
        if rust_path.read_text() != rust:
            raise SystemExit(f"generated file differs: {rust_path}")
    else:
        rust_path.write_text(rust)
    print(json.dumps(report["statistics"], indent=2))


if __name__ == "__main__":
    main()
