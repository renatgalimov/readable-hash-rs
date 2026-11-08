#!/usr/bin/env python3
"""Build overnight comparison artifacts from real outputs (stdlib only).

Inputs: results/sweep.json (compile_dyn exact metrics), results/examples.csv
and a 20k LCG sample TSV, both printed by `cargo run --example
phrase_dyn_comparison`. Cross-checks every Rust dyn encoding against an
independent Python parser of the exported model text, computes proxy
metrics, and writes results/summary.json, results/examples.json,
results/proxy_metrics.csv and results/report.html.
"""
import csv
import gzip
import html
import json
import math
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
RESULTS = ROOT / "results"
CORPORA = Path("/home/agent/corpora/readable-hash-overnight")
MODELS = {"dyn_en_unique": "en-unique", "dyn_en_fineweb": "en-fineweb", "dyn_tr_fineweb": "tr-fineweb"}
COLUMNS = ["v4", "dyn_en_unique", "dyn_en_fineweb", "dyn_tr_fineweb", "dyn_en_unique_mix_v1"]
LANGUAGE = {"v4": "en", "dyn_en_unique": "en", "dyn_en_fineweb": "en", "dyn_tr_fineweb": "tr",
            "dyn_en_unique_mix_v1": "en"}
RISK = {"en": ["fuck", "shit", "cunt", "bitch", "nigg", "fag", "cock", "dick", "piss", "slut", "whore",
               "rape", "porn", "nazi", "twat", "wank", "tits", "anal"],
        "tr": ["orospu", "amcık", "yarak", "piç", "göt", "sik", "amk"]}


class TextModel:
    """Independent reimplementation reading the exported `dynphrase v1` text."""

    def __init__(self, path):
        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines[0] == "dynphrase v1"
        self.name = lines[1].split(" ", 1)[1]
        self.words = int(lines[2].split()[1])
        self.states = []
        for line in lines[4:]:
            row = []
            for item in line.split(" "):
                text, target = item.rsplit(">", 1)
                row.append((text, None if target == "$" else int(target)))
            texts = sorted(text for text, _ in row)
            assert all(not right.startswith(left) for left, right in zip(texts, texts[1:])), "prefix-free"
            self.states.append(row)
        self.count = [0] * len(self.states)
        for index in range(len(self.states) - 1, -1, -1):
            self.count[index] = sum(1 if target is None else self.count[target] for _, target in self.states[index])
        self.width = self.count[0]

    def word(self, rank):
        state, text = 0, ""
        while True:
            for token, target in self.states[state]:
                size = 1 if target is None else self.count[target]
                if rank < size:
                    break
                rank -= size
            text += token
            if target is None:
                return text
            state = target

    def encode(self, value):
        digits = []
        for _ in range(self.words):
            value, digit = divmod(value, self.width)
            digits.append(digit)
        return " ".join(self.word(digit) for digit in reversed(digits))


def char_model(words):
    trigram, bigram, alphabet = Counter(), Counter(), set("$")
    for word, count in words.items():
        padded = "^^" + word + "$"
        alphabet.update(word)
        for index in range(2, len(padded)):
            trigram[padded[index - 2:index + 1]] += count
            bigram[padded[index - 2:index]] += count
    size = len(alphabet)

    def bits(word):
        padded = "^^" + word + "$"
        total = 0.0
        for index in range(2, len(padded)):
            numerator = trigram[padded[index - 2:index + 1]] + 0.01
            denominator = bigram[padded[index - 2:index]] + 0.01 * size
            total -= math.log2(numerator / denominator)
        return total / (len(word) + 1)

    return bits


def counts(language):
    return json.load(gzip.open(CORPORA / f"{language}_counts.json.gz", "rt", encoding="utf-8"))


def proxies(phrases, language, scorer, heldout_vocab, train_vocab):
    words = [word for phrase in phrases for word in phrase.split(" ")]
    lengths = [len(phrase) - phrase.count(" ") for phrase in phrases]
    risk_hits = Counter()
    for phrase in phrases:
        for pattern in RISK[language]:
            if pattern in phrase.replace(" ", ""):
                risk_hits[pattern] += 1
    lengths_sorted = sorted(lengths)
    return {
        "phrases": len(phrases),
        "letters_mean": sum(lengths) / len(lengths),
        "letters_p5_p50_p95": [lengths_sorted[len(lengths) * q // 100] for q in (5, 50, 95)],
        "letters_min_max": [lengths_sorted[0], lengths_sorted[-1]],
        "char_trigram_bits_per_char_heldout": sum(map(scorer, words)) / len(words),
        "real_word_rate_heldout_vocab": sum(word in heldout_vocab for word in words) / len(words),
        "real_word_rate_train_vocab": sum(word in train_vocab for word in words) / len(words),
        "phrases_with_repeated_word": sum(len(set(p.split(" "))) < len(p.split(" ")) for p in phrases) / len(phrases),
        "risk_substring_phrase_rate": sum(risk_hits.values()) / len(phrases),
        "risk_substring_hits": dict(risk_hits.most_common()),
    }


def main():
    sample_path = Path(sys.argv[1])
    sweep = json.loads((RESULTS / "sweep.json").read_text())
    models = {column: TextModel(REPO / "src/dyn_models" / f"{stem}.txt") for column, stem in MODELS.items()}
    with (RESULTS / "examples.csv").open(encoding="utf-8") as handle:
        examples = list(csv.DictReader(handle))
    mismatches = 0
    for row in examples:
        for column, model in models.items():
            mismatches += model.encode(int(row["value"])) != row[column]
    sample = [line.rstrip("\n").split("\t") for line in sample_path.open(encoding="utf-8")]
    for fields in sample[:5000]:
        for offset, column in enumerate(MODELS):
            mismatches += models[column].encode(int(fields[0])) != fields[2 + offset]
    assert mismatches == 0, mismatches
    data = {language: counts(language) for language in ("en", "tr")}
    scorers = {language: char_model({word: value[0] for word, value in data[language]["heldout"].items()})
               for language in data}
    proxy = {}
    for index, column in enumerate(COLUMNS):
        language = LANGUAGE[column]
        phrases = [fields[1 + index] for fields in sample]
        proxy[column] = proxies(phrases, language, scorers[language], data[language]["heldout"], data[language]["train"])
    for language in ("en", "tr"):
        reference = sorted(data[language]["train"], key=lambda word: -data[language]["train"][word][0])[:20000]
        proxy[f"reference_real_{language}_train_words"] = {
            "char_trigram_bits_per_char_heldout": sum(map(scorers[language], reference)) / len(reference),
            "note": "top-20k train-split word types (by occurrences), scored by the heldout char model",
        }
    with (RESULTS / "proxy_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        keys = ["letters_mean", "char_trigram_bits_per_char_heldout", "real_word_rate_heldout_vocab",
                "real_word_rate_train_vocab", "phrases_with_repeated_word", "risk_substring_phrase_rate"]
        writer.writerow(["arm"] + keys)
        for arm, values in proxy.items():
            writer.writerow([arm] + [values.get(key, "") for key in keys])
    (RESULTS / "examples.json").write_text(json.dumps(examples, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest = json.loads((CORPORA / "MANIFEST.json").read_text())
    disk = {
        "corpus_dir_bytes": sum(path.stat().st_size for path in CORPORA.iterdir()),
        "filesystem_free_bytes": shutil.disk_usage("/").free,
        "model_text_bytes": {stem: (REPO / "src/dyn_models" / f"{stem}.txt").stat().st_size for stem in MODELS.values()},
    }
    summary = {
        "cross_check": {"rust_vs_python_mismatches": mismatches, "rows_checked": len(examples) + 5000},
        "selected": {key: {k: v for k, v in value["report"].items()} | {"name": value["name"], "bytes": value["bytes"]}
                     for key, value in sweep["selected"].items()},
        "sweep_compact": [{k: entry.get(k) for k in ("language", "source", "cap", "words", "max_tokens", "word_width_W",
                                                     "log2_capacity", "utilization_2^64_over_capacity",
                                                     "phrase_letters_mean_uniform_u64", "build_seconds", "error")}
                          | {"not_attested_heldout": entry.get("full_grammar_transition_rates", {}).get("not_attested_heldout"),
                             "fallback": entry.get("full_grammar_transition_rates", {}).get("fallback")}
                          for entry in sweep["sweep"]],
        "proxy_metrics_20k_lcg_seed99": proxy,
        "corpus_manifest": manifest,
        "disk": disk,
        "compile_max_rss_mb": sweep["max_rss_mb"],
    }
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    write_html(summary, examples)
    print(json.dumps({"mismatches": mismatches, "proxy": {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv)
                                                                for kk, vv in v.items() if kk != "risk_substring_hits"}
                                                           for k, v in proxy.items()}}, indent=1, ensure_ascii=False))


def table(rows, header):
    escape = lambda value: html.escape(str(value))  # noqa: E731
    head = "".join(f"<th>{escape(name)}</th>" for name in header)
    body = "".join("<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def fmt(value):
    return f"{value:.4f}" if isinstance(value, float) else value


def write_html(summary, examples):
    tests_path = RESULTS / "test_status.txt"
    tests = tests_path.read_text() if tests_path.exists() else "test status not recorded"
    proxy_rows = [[arm] + [fmt(values.get(key, "")) for key in (
        "letters_mean", "char_trigram_bits_per_char_heldout", "real_word_rate_heldout_vocab",
        "phrases_with_repeated_word", "risk_substring_phrase_rate")] for arm, values in summary["proxy_metrics_20k_lcg_seed99"].items()]
    sweep_rows = [[entry[key] if not isinstance(entry[key], float) else fmt(entry[key]) for key in (
        "language", "source", "cap", "words", "max_tokens", "word_width_W", "log2_capacity", "not_attested_heldout",
        "phrase_letters_mean_uniform_u64", "error")] for entry in summary["sweep_compact"]]
    example_rows = [[row["label"], row["value"]] + [row[column] for column in COLUMNS] for row in examples]
    manifest_rows = [[language, entry["dataset"], entry["revision"], entry["file"], entry["license"],
                      entry["bytes_transferred"], entry["clean_utf8_text_bytes"], entry["retained_gzip_bytes"],
                      entry["retained_sha256"]] for language, entry in summary["corpus_manifest"].items()]
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>readable-hash overnight: bounded-grammar rank/unrank (dyn v1)</title>
<style>body{{font-family:sans-serif;margin:2em;max-width:1400px}}table{{border-collapse:collapse;font-size:13px}}
td,th{{border:1px solid #ccc;padding:3px 6px;text-align:left}}th{{background:#eee}}pre{{background:#f6f6f6;padding:1em;white-space:pre-wrap}}
.blocker{{color:#a00}}</style></head><body>
<h1>Experimental bounded-grammar rank/unrank codec (dyn v1) vs phrase v4</h1>
<p>All numbers below were produced by the scripts in <code>models/overnight/</code> and the Rust example
<code>phrase_dyn_comparison</code>; nothing here is human or native-speaker validated. Dyn v1 is experimental and does not
replace v1-v4. Cross-check: {summary['cross_check']['rust_vs_python_mismatches']} Rust/Python mismatches over
{summary['cross_check']['rows_checked']} rows.</p>
<h2>Completed: proxy metrics (20,000 LCG inputs, seed 99)</h2>
<p>Char-trigram bits/char is scored by a model trained on the held-out split of the same-language FineWeb sample
(lower = more English/Turkish-like spelling). Real-word rate counts generated words that occur in that split.
Risk rate counts phrases containing a listed offensive substring (substring matching, many false positives,
for example Turkish "sik" inside "eksik").</p>
{table(proxy_rows, ["arm", "letters/phrase", "char3 bits/char", "real-word rate", "repeated word", "risk substring rate"])}
<h2>Cap sweep (exact grammar counts)</h2>
{table(sweep_rows, ["lang", "source", "cap", "words", "max tokens", "W", "log2 capacity", "heldout-unattested transitions", "mean letters (uniform u64, exact)", "error / blocker"])}
<h2>Examples (every value decoded and asserted in Rust)</h2>
<p>DefaultHasher rows use DefaultHasher::new(), write(bytes), finish(); not stable across Rust versions.
mix_v1 is a separately versioned reversible splitmix64 finalizer applied before encoding; not encryption.</p>
{table(example_rows, ["label", "value"] + COLUMNS)}
<h2>Corpus provenance</h2>
{table(manifest_rows, ["lang", "dataset", "revision", "file", "license", "bytes transferred", "clean text bytes", "retained gzip bytes", "sha256"])}
<h2>Disk</h2><pre>{html.escape(json.dumps(summary['disk'], indent=1))}</pre>
<h2>Tests</h2><pre>{html.escape(tests)}</pre>
<h2 class="blocker">Not done / blockers</h2><ul>
<li>No human or native-speaker readability evaluation.</li>
<li>No @code-review bot was available in this session; self-review only.</li>
<li>Corpus not scaled beyond the 100 MB/language initial sample.</li>
<li>Multilingual selector words not implemented (idea not finalized).</li></ul>
<p>Full write-up: models/OVERNIGHT_REPORT.md</p></body></html>
"""
    (RESULTS / "report_partA.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main()
