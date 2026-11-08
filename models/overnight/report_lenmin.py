#!/usr/bin/env python3
"""Part B artifacts: lenmin_summary.json, lenmin_examples.json and the final
self-contained results/report.html (Part B + the Part A page body).

Inputs: results/lenmin_sweep.json, results/lenmin_examples.csv, the Rust
example (`--sample`) for 20k raw/mixed phrases, a dyn/v4 200k sample TSV
(argument 1, from `phrase_dyn_comparison --sample 200000`), test_status.txt.
"""
import csv
import html
import json
import re
import statistics
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import architect_check  # noqa: E402
import lenmin  # noqa: E402
import report as part_a  # noqa: E402

RESULTS = ROOT / "results"
REPO = ROOT.parent.parent
SELECTED = "lm-en-unique-b256-c64-t5-constrained-cur-w2-4"
RISK = part_a.RISK["en"] + ["sex", "damn", "hell", "crap", "turd", "pee", "poo"]


def fmt(value, digits=2):
    return f"{value:.{digits}f}" if isinstance(value, float) else str(value)


def table(rows, header):
    head = "".join(f"<th>{html.escape(str(cell))}</th>" for cell in header)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row) + "</tr>" for row in rows)
    return f"<table><tr>{head}</tr>{body}</table>"


def baseline_stats(path):
    stats = {"v4": [], "dyn_en_unique": []}
    for line in Path(path).read_text().splitlines():
        fields = line.split("\t")
        stats["v4"].append(len(fields[1]))
        stats["dyn_en_unique"].append(len(fields[2]))
    result = {}
    for name, lengths in stats.items():
        counter = Counter(lengths)
        result[name] = {"mean": statistics.fmean(lengths), "max_observed": max(lengths), "min_observed": min(lengths),
                        "samples": len(lengths), "words": 3, "bits": 64,
                        "histogram": {str(length): count / len(lengths) for length, count in sorted(counter.items())}}
    return result


def pareto(rows):
    """Non-dominated on (mean length, unattested, -real words, nonending, fallback)."""
    def keys(row):
        return (row["length_mean"], row["heldout_unattested_share"], -row["real_word_share"],
                row["nonending_end_share"], row["fallback_share"])

    front = []
    for row in rows:
        mine = keys(row)
        if not any(all(theirs <= ours for theirs, ours in zip(keys(other), mine)) and keys(other) != mine for other in rows):
            front.append(row)
    return sorted(front, key=lambda row: row["length_mean"])


def paired_delta(rows, vary, pairs):
    """Mean length delta when flipping one design switch, all else equal."""
    index = {}
    for row in rows:
        key = tuple(row[name] for name in ("language", "source", "cap_begin", "cap_cont", "max_tokens", "words_min", "words_max")
                    + tuple(field for field in ("ending", "curated") if field != vary))
        index.setdefault(key, {})[row[vary]] = row
    deltas = []
    for group in index.values():
        if all(value in group for value in pairs):
            deltas.append(group[pairs[1]]["length_mean"] - group[pairs[0]]["length_mean"])
    return {"pairs": len(deltas), "mean_delta": statistics.fmean(deltas) if deltas else None,
            "min_delta": min(deltas) if deltas else None, "max_delta": max(deltas) if deltas else None}


def main():
    sweep = json.loads((RESULTS / "lenmin_sweep.json").read_text())
    valid = [row for row in sweep if "error" not in row]
    failed = [row for row in sweep if "error" in row]
    unique = [row for row in valid if row["source"] == "unique"]
    selected = next(row for row in valid if row["name"] == SELECTED)
    name, kmin, kmax, states = lenmin.parse_text((REPO / "src/lenmin_models/en-unique.txt").read_text())
    model = lenmin.LenMin(kmin, kmax, states)
    exact = model.length_stats()
    assert abs(exact["mean"] - selected["length_mean"]) < 1e-9
    baselines = baseline_stats(sys.argv[1])
    # dyn exact mean from Part A (letters only) + 2 spaces
    partial = json.loads((RESULTS / "summary.json").read_text())
    dyn_exact_mean = partial["selected"]["en-unique"]["phrase_letters_mean_uniform_u64"] + 2
    sample = subprocess.run(["cargo", "run", "--quiet", "--release", "--example", "phrase_lenmin_comparison", "--", "--sample", "20000"],
                            cwd=REPO, check=True, capture_output=True, text=True).stdout.splitlines()
    raw = [line.split("\t")[1] for line in sample]
    mixed = [line.split("\t")[2] for line in sample]

    def flags(phrases):
        risky = [phrase for phrase in phrases if any(word in phrase.replace(" ", "") for word in RISK)]
        repeated = [phrase for phrase in phrases if len(set(phrase.split(" "))) < len(phrase.split(" "))]
        return {"phrases": len(phrases), "risk_substring_rate": len(risky) / len(phrases),
                "risk_examples_first5": risky[:5], "repeated_word_rate": len(repeated) / len(phrases),
                "mean_chars": statistics.fmean(len(phrase) for phrase in phrases), "max_chars": max(len(phrase) for phrase in phrases)}

    examples = list(csv.DictReader((RESULTS / "lenmin_examples.csv").open(encoding="utf-8")))
    awkward = [row["label"] + ": " + row["lenmin_raw"] for row in examples
               if len(row["lenmin_raw"].split(" ")) == 2 and len(row["lenmin_raw"]) <= 6]
    front = {}
    for source, language in (("unique", "en"), ("fineweb-occ", "en"), ("fineweb-occ", "tr")):
        front[f"{language}-{source}"] = pareto([row for row in valid if row["source"] == source and row["language"] == language])
    summary = {
        "selected": {key: value for key, value in selected.items() if key != "length_hist"},
        "selection_rule": ("Fixed before inspecting examples: among English unique-word arms with fallback share <= 1% and "
                           "ending-constrained words (every multi-token word ends in a corpus ending token; one-token words "
                           "only from the curated real-word list), pick the minimum exact mean length "
                           "(letters + spaces) over uniform u64; ties -> smaller max, fewer tokens per word (<=5), then smaller begin cap."),
        "exact_length_uniform_u64": {key: value for key, value in exact.items() if key != "histogram"} | {"histogram": exact["histogram"]},
        "baselines_sampled_200k_lcg": baselines,
        "dyn_exact_mean_chars": dyn_exact_mean,
        "headline": [
            {"codec": "v4", "words": 3, "bits": 64, "mean_chars": baselines["v4"]["mean"], "max_chars": baselines["v4"]["max_observed"], "note": "sampled 200k"},
            {"codec": "dyn v1 en-unique", "words": 3, "bits": 64, "mean_chars": dyn_exact_mean,
             "max_chars": baselines["dyn_en_unique"]["max_observed"], "note": "mean exact; max sampled 200k"},
            {"codec": "lenmin v1 (selected)", "words": f"{kmin}-{kmax} (mean {selected['sample_words_per_phrase']:.2f})",
             "bits": 64, "mean_chars": exact["mean"], "max_chars": exact["max"], "note": "exact"},
        ],
        "sample_flags_20k": {"lenmin_raw": flags(raw), "lenmin_mix_v1": flags(mixed)},
        "raw_awkward_small_values": awkward,
        "switch_costs_unique_english": {
            "curated_real_one_token_words": paired_delta(unique, "curated", (True, False)),
            "ending_constrained_vs_free": paired_delta(unique, "ending", ("free", "constrained")),
        },
        "architect_idealised_check": architect_check.analysis(),
        "architect_idealised_check_t5": architect_check.analysis(128, 64, 3, 5),
        "sweep": {"arms": len(sweep), "valid": len(valid), "insufficient_capacity_or_error": len(failed),
                  "pareto": {key: [{key: value for key, value in row.items() if key != "length_hist"} for row in rows] for key, rows in front.items()}},
    }
    (RESULTS / "lenmin_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (RESULTS / "lenmin_examples.json").write_text(json.dumps(examples, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    write_html(summary, examples, front, valid, failed)
    print("wrote", RESULTS / "report.html")


def write_html(summary, examples, front, valid, failed):
    head = [[row["codec"], row["words"], row["bits"], fmt(row["mean_chars"]), row["max_chars"], row["note"]] for row in summary["headline"]]
    hist = summary["exact_length_uniform_u64"]["histogram"]
    hist_rows = [[length, f"{share:.6g}"] for length, share in hist.items()]
    columns = ("name", "length_mean", "length_max", "log2_capacity", "heldout_unattested_share", "real_word_share",
               "nonending_end_share", "fallback_share")
    pareto_sections = ""
    for key, rows in front.items():
        shown = rows[:40]
        pareto_sections += f"<h3>Pareto frontier: {html.escape(key)} ({len(rows)} non-dominated arms, first {len(shown)} by mean length)</h3>" + table(
            [[fmt(row[column], 3) if isinstance(row[column], float) else row[column] for column in columns] for row in shown], columns)
    sweep_rows = sorted(valid, key=lambda row: row["length_mean"])
    sweep_table = table([[fmt(row[column], 3) if isinstance(row[column], float) else row[column] for column in columns] for row in sweep_rows], columns)
    example_rows = [[row["label"], row["value"], row["v4"], row["dyn_en_unique"], row["lenmin_raw"], len(row["lenmin_raw"]),
                     row["lenmin_mix_v1"], len(row["lenmin_mix_v1"])] for row in examples]
    costs = summary["switch_costs_unique_english"]
    flag = summary["sample_flags_20k"]
    body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>readable-hash overnight: length-minimized codec (lenmin v1) and bounded grammar (dyn v1)</title>
<style>body{{font-family:sans-serif;margin:2em;max-width:1500px}}table{{border-collapse:collapse;font-size:13px}}
td,th{{border:1px solid #ccc;padding:3px 6px;text-align:left}}th{{background:#eee}}pre{{background:#f6f6f6;padding:1em;white-space:pre-wrap}}
.blocker{{color:#a00}}</style></head><body>
<h1>Part B: length-minimized reversible u64 phrases (lenmin v1)</h1>
<p>Experimental, alongside v1-v4 and dyn v1 (nothing replaced). Length = letters + spaces. All 64 bits are kept: the codec is an exact,
injective bijection between u64 and phrases; the 2<sup>64</sup> shortest phrases of the grammar are used (length-major order).
Nothing here is human or native-speaker validated. No security claim; repetition is not eliminated.</p>
<h2>Headline (uniform u64)</h2>
{table(head, ["codec", "words", "bits kept", "mean letters+spaces", "max letters+spaces", "how measured"])}
<p>Selected arm: <code>{html.escape(SELECTED)}</code>: words 2-4 separated by spaces, 1-5 tokens/word, begin cap 256, continuation cap 64,
ending-constrained, curated real one-token words. Grammar capacity log2 = {summary['selected']['log2_capacity']:.2f} bits; only the
first 2<sup>64</sup> (shortest) phrases are used. Exact length distribution (share of u64 values):</p>
{table(hist_rows, ["total length", "share of values"])}
<p>Selection rule (fixed in advance): {html.escape(summary['selection_rule'])}</p>
<h2>Cost of design switches (English unique-word arms, paired, mean-length difference in chars)</h2>
<pre>{html.escape(json.dumps(costs, indent=1))}</pre>
<h2>Sample flags (20,000 LCG values, Rust)</h2>
<pre>{html.escape(json.dumps(flag, indent=1, ensure_ascii=False))}</pre>
<p>Raw (unmixed) small values map to the shortest phrases and look awkward/repetitive: {html.escape(', '.join(summary['raw_awkward_small_values']))}.
The mix_v1 column applies the invertible splitmix64 finalizer first. It spreads structured inputs; it is not encryption.</p>
<h2>Examples ({len(examples)} fixed inputs; each decoded and asserted in Rust; Python reference cross-checked)</h2>
<p>DefaultHasher rows use DefaultHasher::new(), write(bytes), finish(); its output is not stable across Rust versions.</p>
{table(example_rows, ["label", "value", "v4", "dyn v1 en-unique", "lenmin raw", "len", "lenmin mix_v1", "len"])}
<h2>Design-space sweep</h2>
<p>{summary['sweep']['arms']} arms, {summary['sweep']['valid']} reach 2<sup>64</sup> capacity; {summary['sweep']['insufficient_capacity_or_error']}
rejected for insufficient capacity (no nonsense padding). Sampled proxies use 5,000 uniform u64 per arm (seeded). heldout_unattested_share is
the share of transitions never seen in the held-out split; it is not comparable across sources (the unique-word source is trained on a dictionary,
held-out is running FineWeb text). nonending_end_share = words that end on a non-ending token.</p>
{pareto_sections}
<h3>All valid arms by mean length</h3>{sweep_table}
<h2 class="blocker">Not done / blockers (not results)</h2><ul>
<li>No human or native-speaker readability evaluation; readability proxies are corpus statistics only.</li>
<li>Selected phrases are mostly fragment-like pseudo-words; the length gain comes from using many more tokens per letter. Quality gap versus real words is large.</li>
<li>Turkish and FineWeb arms exist only as sweep arms (not shipped as frozen Rust models).</li>
<li>Multilingual selector words still not designed.</li></ul>
<hr><h1>Part A (dyn v1 bounded grammar, previous run)</h1>
"""
    partial = (RESULTS / "report_partA.html").read_text(encoding="utf-8")
    match = re.search(r"<body>(.*)</body>", partial, re.S)
    assert match
    inner = match.group(1)
    inner = inner.replace("<h1>", "<h2 style=\"font-size:1.4em\">", 1).replace("</h1>", "</h2>", 1)
    (RESULTS / "report.html").write_text(body + inner + "</body></html>\n", encoding="utf-8")


if __name__ == "__main__":
    main()
