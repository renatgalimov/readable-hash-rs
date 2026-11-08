#!/usr/bin/env python3
"""Python reference vs Rust: 20k LCG samples (raw and mix v1) + the fixed example CSV."""
import csv
import io
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lenmin  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
SAMPLES = 20000


def run(*arguments):
    return subprocess.run(["cargo", "run", "--quiet", "--release", "--example", "phrase_lenmin_comparison", "--", *arguments],
                          cwd=REPO, check=True, capture_output=True, text=True).stdout


def main():
    name, kmin, kmax, states = lenmin.parse_text((REPO / "src/lenmin_models/en-unique.txt").read_text())
    model = lenmin.LenMin(kmin, kmax, states)
    mismatches = checked = 0
    for line in run("--sample", str(SAMPLES)).splitlines():
        value, raw, mixed = line.split("\t")
        value = int(value)
        for phrase, expected_value, expected_phrase in ((raw, value, model.encode(value)),
                                                         (mixed, value, model.encode(lenmin.mix(value)))):
            checked += 1
            mismatches += phrase != expected_phrase
            mismatches += model.decode(phrase) not in (value, lenmin.mix(value))
    rows = list(csv.DictReader(io.StringIO(run())))
    for row in rows:
        value = int(row["value"])
        checked += 2
        mismatches += row["lenmin_raw"] != model.encode(value)
        mismatches += row["lenmin_mix_v1"] != model.encode(lenmin.mix(value))
        mismatches += model.decode(row["lenmin_raw"]) != value
    print(f"model={name} checked={checked} example_rows={len(rows)} mismatches={mismatches}")
    sys.exit(1 if mismatches else 0)


if __name__ == "__main__":
    main()
