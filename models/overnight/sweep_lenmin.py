#!/usr/bin/env python3
"""Design-space sweep for the length-major codec. Appends JSON lines to
results/lenmin_sweep.jsonl (resumable) and writes results/lenmin_sweep.json."""
import itertools
import json
import sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compile_lenmin  # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results"
OUT = RESULTS / "lenmin_sweep.jsonl"
SAMPLES = 5000


def arm_name(arm):
    language, source, begin, cont, tokens, ending, curated, low, high = arm
    return (f"lm-{language}-{source}-b{begin}-c{cont}-t{tokens}-{ending}-{'cur' if curated else 'nocur'}-w{low}"
            + (f"-{high}" if high != low else ""))


def arms():
    words = [(2, 2), (3, 3), (4, 4), (2, 4)]
    for (kmin, kmax), tokens, begin, cont, ending, curated in itertools.product(
            words, (3, 4, 5, 6), (128, 256), (16, 32, 64), ("free", "constrained"), (True, False)):
        if tokens == 6 and kmin > 2:
            continue
        if tokens == 3 and (kmin, kmax) == (2, 2):
            continue
        yield ("en", "unique", begin, cont, tokens, ending, curated, kmin, kmax)
    for language, source in (("en", "fineweb-occ"), ("tr", "fineweb-occ")):
        for (kmin, kmax), tokens, begin, cont, ending in itertools.product(
                ((3, 3), (2, 4)), (4, 5), (128, 256), (32, 64), ("free", "constrained")):
            yield (language, source, begin, cont, tokens, ending, language == "en", kmin, kmax)


def run(arm):
    try:
        result, _, _ = compile_lenmin.evaluate(*arm, samples=SAMPLES)
    except Exception as error:  # record, do not hide
        result = dict(name=arm_name(arm), arm=list(arm), error=f"{type(error).__name__}: {error}")
    return result


def main():
    done = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            done.add(json.loads(line).get("name"))
    todo = [arm for arm in arms() if arm_name(arm) not in done]
    print(len(todo), "arms to run", flush=True)
    with Pool(3) as pool, OUT.open("a") as sink:
        for result in pool.imap_unordered(run, todo):
            sink.write(json.dumps(result, ensure_ascii=False) + "\n")
            sink.flush()
    rows = [json.loads(line) for line in OUT.read_text().splitlines()]
    (RESULTS / "lenmin_sweep.json").write_text(json.dumps(rows, ensure_ascii=False) + "\n")
    print("rows", len(rows), "valid", sum("error" not in row for row in rows))


if __name__ == "__main__":
    main()
