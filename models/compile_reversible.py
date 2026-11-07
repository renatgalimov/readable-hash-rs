#!/usr/bin/env python3
"""Compile the immutable reversible v1 tables from the checked-in corpus."""
import argparse
import json
from collections import Counter
from pathlib import Path

from reversible_tables import choose_prefix_free, load_training_counts

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "models/training-data"


def prefix_capacity(texts):
    return sum(not any(other != text and other.startswith(text) for other in texts)
               for text in texts)


def compile_tables():
    model = json.loads((DATA / "english-lowercase-model.json").read_text(encoding="utf-8"))
    counts = load_training_counts(DATA / "english-lowercase.txt", DATA / "english-lowercase-model.json")
    tokens = model["id_to_token"]
    beginning = {tokens[index][1:]: index for index in range(256) if tokens[index].startswith("^")}
    # The trainer can fall back to a middle token at the start (notably x).
    for index in counts["begin"]:
        text = tokens[index].removeprefix("^").removesuffix("$")
        if text.isascii() and text.isalpha() and text.islower():
            beginning.setdefault(text, index)
    middle = {tokens[index]: index for index in range(512, 1024) if tokens[index].islower() and tokens[index].isalpha() and tokens[index].isascii()}
    ending = {tokens[index][:-1]: index for index in range(256, 512) if tokens[index].endswith("$")}
    begin_choices = choose_prefix_free({text: (counts["begin"][index], 0) for text, index in beginning.items()}, prefix_capacity(beginning))
    begin_ids = [beginning[text] for text in begin_choices]
    contexts = list(range(256)) + list(range(512, 1024))
    rows = {}
    omissions = {}
    for label, pool, size in (("middle", middle, 32), ("end", ending, 16)):
        global_counts = sum(counts[label].values(), Counter())
        tables = []
        omitted = []
        for context in contexts:
            local = counts[label].get(context, {})
            if not set(local).issubset(pool.values()):
                raise ValueError(f"ineligible {label} transition in context {tokens[context]}")
            candidates = {text: (local.get(index, 0), 0 if local.get(index, 0) else global_counts[index]) for text, index in pool.items()}
            choices = choose_prefix_free(candidates, size)
            chosen = set(choices)
            omitted.append([tokens[index] for index in sorted(local) if index in pool.values() and tokens[index].removesuffix("$") not in chosen])
            tables.append([pool[text] for text in choices])
        rows[label] = tables
        omissions[label] = omitted
    metrics = {"corpus_words": counts["word_count"], "beginning_capacity": len(begin_ids),
               "middle_pool": len(middle), "ending_pool": len(ending),
               "contexts": len(contexts),
               "middle_omitted_local_total": sum(map(len, omissions["middle"])),
               "ending_omitted_local_total": sum(map(len, omissions["end"])),
               "s_context_id": model["vocab"]["^s"],
               "s_middle_local": len(counts["middle"].get(model["vocab"]["^s"], {})),
               "s_middle_omitted": omissions["middle"][model["vocab"]["^s"]]}
    report = {label: {tokens[context]: omitted for context, omitted in zip(contexts, entries) if omitted}
              for label, entries in omissions.items()}
    return begin_ids, rows, metrics, report, tokens


def render(beginning, rows, tokens):
    lines = ["//! Generated reversible format v1; do not edit.",
             "// Regenerate with python models/compile_reversible.py", "",
             "#[rustfmt::skip]", "pub static TOKENS: [&str; 1024] = ["]
    lines += ["    " + json.dumps(token) + "," for token in tokens]
    lines += ["];", "",
             "#[rustfmt::skip]", f"pub static BEGIN: [u16; {len(beginning)}] = [",
             "    " + ", ".join(map(str, beginning)) + ",", "];", ""]
    for label, size in (("middle", 32), ("end", 16)):
        lines += ["#[rustfmt::skip]", f"pub static {label.upper()}: [[u16; {size}]; 768] = ["]
        lines += ["    [" + ", ".join(map(str, row)) + "]," for row in rows[label]]
        lines += ["];", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    beginning, rows, metrics, report, tokens = compile_tables()
    output = render(beginning, rows, tokens)
    report_output = json.dumps({"metrics": metrics, "omitted_local_tokens": report}, indent=2, sort_keys=True) + "\n"
    path = ROOT / "src/reversible_v1_data.rs"
    report_path = ROOT / "models/reversible_v1_report.json"
    if args.check:
        if path.read_text(encoding="utf-8") != output or report_path.read_text(encoding="utf-8") != report_output:
            raise SystemExit("generated tables differ")
    else:
        path.write_text(output, encoding="utf-8")
        report_path.write_text(report_output, encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
