#!/usr/bin/env python3
"""Rank every experiment in results/ and write REPORT.md plus report.html (with sample phrases to judge by eye).

    python3 report.py
"""
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
LANGS = Path.home() / "data" / "phrase-langs" / "words" / "languages.json"

COLUMNS = [
    ("chars", "chars", "average characters per phrase"),
    ("consonant_runs_pct", "3+ cons. %", "words with 3+ consonants in a row"),
    ("english_words_pct", "EN words %", "words that are real English words"),
    ("own_words_pct", "own words %", "words that are real words of the table's language(s)"),
    ("offensive_whole_english_list_pct", "EN list %", "phrases with a whole word from an English offensive list"),
    ("offensive_severe_en_pct", "EN severe %", "phrases with a severe English term (whole, or inside a word if 5+ letters)"),
    ("offensive_whole_own_list_pct", "own list %", "phrases with a whole word from the table language's own list"),
    ("offensive_whole_major_lists_pct", "major lists %", "phrases with a whole word from the lists of 13 most-spoken languages"),
    ("offensive_whole_pct", "any list %", "phrases with a whole word from any language's list"),
    ("offensive_inside5_pct", "inside 5+ %", "phrases with a listed term of 5+ letters inside a word"),
    ("relaxed_rows", "relaxed rows", "table rows (of 768) that needed the join rule relaxed"),
]


def score(result):
    """Lower is better: offensiveness first (major lists, severe English), then hard-to-say words, then length."""
    return (result["offensive_whole_major_lists_pct"] * 4 + result["offensive_severe_en_pct"] * 8
            + result["offensive_inside5_pct"] + result["consonant_runs_pct"] / 10
            + max(0, result["chars"] - 28) / 2 + result["relaxed_rows"] / 50)


def main():
    languages = json.loads(LANGS.read_text()) if LANGS.exists() else {}
    results = [json.loads(p.read_text()) for p in sorted(RESULTS.glob("*.json")) if not p.name.endswith(".model.json")]
    failed = [r for r in results if r.get("failed")]
    results = sorted((r for r in results if not r.get("failed")), key=score)
    baseline = next((r for r in results if r["name"] == "en-v5"), None)

    def label(r):
        codes = r.get("languages", [])
        names = " + ".join(languages.get(c, {}).get("name", c) for c in codes) or r["name"]
        return f"{names} ({r['name']})"

    lines = ["# Multilingual phrase tables: offensiveness vs. readability", "",
             f"{len(results)} tables built with the frozen v5 compiler and rules; each encodes the same 20,000 random "
             "64-bit values. Lower is better in every column except the word columns. Ranked by a combined score "
             "(offensive words first, then hard-to-say words, then length).", ""]
    if baseline:
        lines += [f"Baseline, today's English tables: {baseline['chars']} chars, "
                  f"{baseline['offensive_whole_english_list_pct']}% English-list hits, "
                  f"{baseline['offensive_severe_en_pct']}% severe, {baseline['offensive_whole_major_lists_pct']}% major lists.", ""]
    lines += ["| # | tables | " + " | ".join(c[1] for c in COLUMNS) + " | sample |",
              "|---|---|" + "---:|" * len(COLUMNS) + "---|"]
    for rank, r in enumerate(results, 1):
        lines.append(f"| {rank} | {label(r)} | " + " | ".join(str(r.get(c[0], "")) for c in COLUMNS)
                     + f" | {r['samples'][0]} |")
    lines += ["", "Columns:"] + [f"- **{c[1]}**: {c[2]}." for c in COLUMNS]
    if failed:
        lines += ["", "Failed builds: " + ", ".join(f"{r['name']} ({r['failed'][:80]})" for r in failed)]
    (HERE / "RESULTS_TABLE.md").write_text("\n".join(lines) + "\n")

    cells = []
    for rank, r in enumerate(results, 1):
        hits = "; ".join(f"{html.escape(t)} ×{n} ({','.join(l)})" for t, n, l, _ in r["top_hits"][:6])
        cells.append(f"<tr><td>{rank}</td><td>{html.escape(label(r))}</td>"
                     + "".join(f"<td>{r.get(c[0], '')}</td>" for c in COLUMNS)
                     + f"<td class=s>{'<br>'.join(html.escape(s) for s in r['samples'][:8])}</td>"
                     + f"<td class=h>{hits}</td></tr>")
    page = f"""<!doctype html><meta charset=utf-8><title>Multilingual phrase tables</title>
<style>body{{font:13px system-ui;margin:20px}}table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:4px 6px;
vertical-align:top}}td.s{{font:12px ui-monospace,monospace;white-space:nowrap}}td.h{{font-size:11px;color:#555;max-width:260px}}
th{{position:sticky;top:0;background:#f4f4f4}}</style>
<h1>Multilingual phrase tables</h1><p>{len(results)} tables, same 20,000 random values each, ranked best first.</p>
<table><tr><th>#</th><th>tables</th>{''.join(f'<th title="{html.escape(c[2])}">{c[1]}</th>' for c in COLUMNS)}
<th>sample phrases</th><th>top offensive hits (lists)</th></tr>{''.join(cells)}</table>"""
    (HERE / "report.html").write_text(page)
    print(f"ranked {len(results)} tables, {len(failed)} failed -> RESULTS_TABLE.md, report.html")


if __name__ == "__main__":
    main()
