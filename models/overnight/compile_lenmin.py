#!/usr/bin/env python3
"""Builder + exact/sampled metrics for length-major "lenmin v1" phrase models.

Word grammar (per arm):
  start row   curated real 1-token words, then beginning (^) tokens
  later rows  per (slot, previous token) context: corpus-supported tokens by
              quality, prefix-free, capped; backoff only if below `floor`
  ending      "constrained": word = B M* E (E tokens end the word);
              "free": a word may stop after any token (only curated real
              words may stop after the first token).
Everything about ordering/ranking lives in lenmin.py.
"""
import argparse
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compile_dyn as dyn  # noqa: E402
import lenmin  # noqa: E402

CURATED_PRIORITY = (
    "the and for her can car con pro sub over inter out "
    "to of in is it on at as an am be he me we my by do go no so or up us if hi ad ex "
    "a i"
).split()
# Excluded on purpose (not exhaustive): slurs/obscenities and "ho".
CURATED_EXCLUDED = ["ho"]
SAMPLE_SEED = 20261107


def conflict(text, others):
    return any(text.startswith(other) or other.startswith(text) for other in others)


def build(language, source, cap_begin, cap_cont, max_tokens, ending, curated, floor=2, min_types=2, cache={}):
    key = (language, source)
    if key not in cache:
        vocab, note = dyn.vocabulary(language)
        weights = dyn.load_words(source, language)
        weight, types = dyn.transitions(weights, vocab)
        heldout_words = dyn.load_heldout(language)
        heldout_weight, _ = dyn.transitions(heldout_words, vocab)
        by_context, global_weight = defaultdict(dict), Counter()
        for (previous, following), value in weight.items():
            by_context[previous][following] = value
            global_weight[following] += value
        usable = [token for token in vocab if dyn.emitted(token) and set(dyn.emitted(token)) <= dyn.ALPHABETS[language]]
        classes = defaultdict(list)
        for token in usable:
            classes[dyn.token_class(token)].append(token)
        cache[key] = dict(vocab=vocab, note=note, weights=weights, types=types, by_context=by_context,
                          global_weight=global_weight, classes=classes, heldout_weight=heldout_weight,
                          real=set(weights) | set(heldout_words))
    data = cache[key]
    by_context, global_weight, types, classes = data["by_context"], data["global_weight"], data["types"], data["classes"]
    heldout_weight = data["heldout_weight"]

    def pick(pool, previous, cap, forced=()):
        local = by_context.get(previous, {})
        quality = sorted(pool, key=lambda token: (-local.get(token, 0), -global_weight[token], dyn.emitted(token)))
        chosen, texts = [], []
        for token in forced:
            chosen.append((token, False))
            texts.append(dyn.emitted(token))
        for token in quality:
            if local.get(token, 0) == 0 or len(chosen) >= cap:
                break
            text = dyn.emitted(token)
            if types[previous, token] < min_types or conflict(text, texts):
                continue
            chosen.append((token, False))
            texts.append(text)
        if len(chosen) < floor:
            for token in sorted(pool, key=lambda token: (-global_weight[token], dyn.emitted(token))):
                if len(chosen) >= floor:
                    break
                text = dyn.emitted(token)
                if not conflict(text, texts):
                    chosen.append((token, True))
                    texts.append(text)
        return chosen

    # ---- start row: curated words first (prefix-free greedy), then B tokens
    begin_texts = {dyn.emitted(token): token for token in classes["B"]}
    curated_words = []
    if curated:
        for word in CURATED_PRIORITY:
            if word in CURATED_EXCLUDED or not set(word) <= dyn.ALPHABETS[language] or language != "en":
                continue
            if not conflict(word, curated_words):
                curated_words.append(word)
    start = []  # (text, kind, token) kind: "curated-begin" | "curated-leaf" | "begin"
    for word in curated_words:
        start.append((word, "curated-begin" if word in begin_texts else "curated-leaf", begin_texts.get(word)))
    forced_texts = [w for w in curated_words]
    local = by_context.get(None, {})
    quality = sorted(classes["B"], key=lambda token: (-local.get(token, 0), -global_weight[token], dyn.emitted(token)))
    removed = 0
    for token in quality:
        text = dyn.emitted(token)
        if local.get(token, 0) == 0 or len(start) >= cap_begin:
            break
        if types[None, token] < min_types:
            continue
        if conflict(text, forced_texts):
            if text not in forced_texts:
                removed += 1
            continue
        start.append((text, "begin", token))
        forced_texts.append(text)
    if len(start) < floor:
        raise ValueError("start row too small")

    # ---- remaining states
    states, index, queue = [], {}, []
    meta = []  # parallel: per state list of choice dicts

    def state_id(key):
        if key not in index:
            index[key] = len(index)
            queue.append(key)
        return index[key]

    state_id(("S",))
    curated_set = set(curated_words)
    while queue:
        key = queue.pop(0)
        accept, row, info = False, [], []
        if key == ("S",):
            for text, kind, token in start:
                if kind == "curated-leaf":
                    target = state_id(("leaf", text))
                else:
                    target = state_id((1, token))
                row.append((text, target))
                info.append(dict(fallback=False, heldout=True if kind != "begin" else heldout_weight[None, token] > 0,
                                 cls="B", kind=kind))
        elif key[0] in ("leaf", "T"):
            accept = True
        else:
            slot, previous = key
            accept = (dyn.emitted(previous) in curated_set) if slot == 1 else (ending == "free" and slot >= 2)
            if slot < max_tokens:
                last = slot == max_tokens - 1
                if ending == "constrained" and last:
                    pool = classes["E"]
                else:
                    pool = classes["M"] + classes["E"]
                for token, fallback in pick(pool, previous, cap_cont):
                    if dyn.token_class(token) == "E":
                        target = state_id(("T",))
                    else:
                        target = state_id((slot + 1, token))
                    row.append((dyn.emitted(token), target))
                    info.append(dict(fallback=fallback, heldout=heldout_weight[previous, token] > 0,
                                     cls=dyn.token_class(token), kind="cont"))
            if ending == "constrained" and slot == max_tokens:
                raise AssertionError("unreachable")
            if not row and not accept:
                raise ValueError(f"dead state {key}")
        states.append((accept, row))
        meta.append(info)
    # relabel topologically: start, then by slot, shared terminals last
    keys = sorted(index, key=lambda state_key: (0 if state_key == ("S",) else 99 if state_key[0] in ("leaf", "T") else state_key[0], index[state_key]))
    relabel = {index[state_key]: number for number, state_key in enumerate(keys)}
    states = [(states[index[state_key]][0], [(text, relabel[target]) for text, target in states[index[state_key]][1]]) for state_key in keys]
    meta = [meta[index[state_key]] for state_key in keys]
    for number, (accept, row) in enumerate(states):
        for text, target in row:
            assert target > number
    return states, meta, dict(curated=curated_words, begin_removed_by_curated=removed, data=data)


def evaluate(language, source, cap_begin, cap_cont, max_tokens, ending, curated, kmin, kmax,
             samples=20000, floor=2, min_types=2, export=None):
    started = time.time()
    states, meta, extra = build(language, source, cap_begin, cap_cont, max_tokens, ending, curated, floor, min_types)
    name = f"lm-{language}-{source}-b{cap_begin}-c{cap_cont}-t{max_tokens}-{ending}-{'cur' if curated else 'nocur'}-w{kmin}" + (f"-{kmax}" if kmax != kmin else "")
    arm = dict(language=language, source=source, cap_begin=cap_begin, cap_cont=cap_cont, max_tokens=max_tokens,
               ending=ending, curated=curated, words_min=kmin, words_max=kmax, name=name)
    text = lenmin.export_text(name, kmin, kmax, states)
    _, _, _, parsed = lenmin.parse_text(text)
    assert parsed == states
    try:
        model = lenmin.LenMin(kmin, kmax, parsed)
    except ValueError as error:
        arm["error"] = str(error)
        return arm, None, None
    stats = model.length_stats()
    arm.update(
        states=len(states), choices=sum(len(row) for _, row in states),
        start_choices=len(states[0][1]), curated_words=extra["curated"], begin_removed_by_curated=extra["begin_removed_by_curated"],
        word_types=sum(model.word_count), max_word_letters=model.maxlen,
        log2_capacity=model.log2_capacity(), log2_utilization=64 - model.log2_capacity(),
        length_mean=stats["mean"], length_min=stats["min"], length_max=stats["max"], length_median=stats["median"],
        length_p99=stats["p99"], length_hist=stats["histogram"], text_bytes=len(text.encode()),
    )
    # sampled proxies (uniform u64, seeded)
    rng = random.Random(SAMPLE_SEED)
    flags = {}
    for number, (_, row) in enumerate(states):
        for position, (token, _) in enumerate(row):
            flags[number, token] = meta[number][position]
    real = extra["data"]["real"]
    transitions = fallback = unattested = words = real_words = tokens = ends_off_class = k_hist = 0
    k_counter, token_counter = Counter(), Counter()
    one_token_words = 0
    for _ in range(samples):
        phrase, paths = model.encode(rng.getrandbits(64), with_path=True)
        k_counter[len(paths)] += 1
        for word, path in zip(phrase.split(" "), paths):
            words += 1
            real_words += word in real
            token_counter[len(path)] += 1
            one_token_words += len(path) == 1
            for state, token in path:
                info = flags[state, token]
                transitions += 1
                fallback += info["fallback"]
                unattested += not info["heldout"]
            last = flags[path[-1]]
            ends_off_class += last["cls"] != "E" and len(path) > 1
    arm.update(
        sample_size=samples, sample_seed=SAMPLE_SEED,
        sample_words_per_phrase=words / samples,
        word_count_dist={str(k): v / samples for k, v in sorted(k_counter.items())},
        tokens_per_word_dist={str(k): v / words for k, v in sorted(token_counter.items())},
        fallback_share=fallback / transitions, heldout_unattested_share=unattested / transitions,
        real_word_share=real_words / words, nonending_end_share=ends_off_class / words,
        one_token_word_share=one_token_words / words,
        build_seconds=round(time.time() - started, 2),
    )
    if export:
        Path(export).write_text(text, encoding="utf-8")
    return arm, model, text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", default="en")
    parser.add_argument("--source", default="unique")
    parser.add_argument("--cap-begin", type=int, default=256)
    parser.add_argument("--cap-cont", type=int, default=32)
    parser.add_argument("--max-tokens", type=int, default=4)
    parser.add_argument("--ending", choices=["free", "constrained"], default="free")
    parser.add_argument("--no-curated", action="store_true")
    parser.add_argument("--words", default="3", help="3 or 2-4")
    parser.add_argument("--samples", type=int, default=5000)
    parser.add_argument("--export")
    args = parser.parse_args()
    low, _, high = args.words.partition("-")
    arm, model, _ = evaluate(args.language, args.source, args.cap_begin, args.cap_cont, args.max_tokens, args.ending,
                             not args.no_curated, int(low), int(high or low), args.samples, export=args.export)
    arm.pop("length_hist", None)
    print(json.dumps(arm, indent=1, ensure_ascii=False))
    if model:
        for value in (0, 1, 2, 42, 1000, 123456789, (1 << 63) - 1, 1 << 63, (1 << 64) - 2, (1 << 64) - 1):
            phrase = model.encode(value)
            assert model.decode(phrase) == value
            print(value, repr(phrase), len(phrase))


if __name__ == "__main__":
    main()
