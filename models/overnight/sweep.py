#!/usr/bin/env python3
"""Run the cap sweep for every arm, select one cap per frozen model, export.

Selection rule (fixed before looking at examples): among configurations with
3 words and W^3 >= 2^64, choose the cap with the lowest held-out
not-attested transition rate; ties -> smaller cap. Words have at most 5
tokens (4 was measured insufficient for 3 words at every cap).
"""
import json
import resource
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compile_dyn  # noqa: E402

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
RUST = ROOT.parent.parent / "src" / "dyn_models"
ARMS = [
    ("en", "unique", 5, 3, "en-unique"),
    ("en", "fineweb-occ", 5, 3, "en-fineweb"),
    ("en", "fineweb-type", 5, 3, None),
    ("tr", "fineweb-occ", 5, 3, "tr-fineweb"),
    ("tr", "fineweb-type", 5, 3, None),
    ("en", "unique", 4, 4, None),
]
CAPS = [16, 32, 64, 128, 256]


def main():
    RESULTS.mkdir(exist_ok=True)
    RUST.mkdir(exist_ok=True)
    sweep, selected = [], {}
    for language, source, max_tokens, words, export in ARMS:
        best = None
        for cap in CAPS:
            started = time.time()
            try:
                states, codec, report = compile_dyn.compile_arm(language, source, cap, 2, words, max_tokens, 2)
            except ValueError as error:
                report, states = {"language": language, "source": source, "cap": cap, "words": words,
                                  "max_tokens": max_tokens, "error": str(error)}, None
            report["build_seconds"] = round(time.time() - started, 2)
            sweep.append(report)
            print(json.dumps({key: report.get(key) for key in ("language", "source", "cap", "words", "max_tokens",
                                                               "log2_capacity", "error")}), flush=True)
            if states and words == 3:
                score = report["full_grammar_transition_rates"]["not_attested_heldout"]
                if best is None or score < best[0]:
                    best = (score, cap, states, report)
        if export and best:
            _, cap, states, report = best
            name = f"{language}-{source}-cap{cap}-t{max_tokens}-w{words}"
            text = compile_dyn.export_text(states, name, words)
            (RUST / f"{export}.txt").write_text(text, encoding="utf-8")
            selected[export] = {"name": name, "cap": cap, "bytes": len(text.encode()), "report": report}
    usage = resource.getrusage(resource.RUSAGE_SELF)
    (RESULTS / "sweep.json").write_text(json.dumps({"sweep": sweep, "selected": selected,
                                                    "max_rss_mb": usage.ru_maxrss / 1024},
                                                   indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: (value["name"], value["bytes"]) for key, value in selected.items()}))


if __name__ == "__main__":
    main()
