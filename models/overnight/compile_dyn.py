#!/usr/bin/env python3
"""Experimental bounded-grammar rank/unrank phrase models ("dyn v1").

Not a replacement for v1-v4. A word is B (M|E){0..2} E: 2..4 tokens, explicit
end tokens, bounded. Each state is (slot, previous token). Each state's choices
are prefix-free over emitted text, ordered by quality (local weight, global
weight, text). A phrase is `words` independent words; the u64 is a rank in
[0, W^words) written base W, first word most significant. Inside a word the
rank is unranked through contiguous subtree-count intervals. No modulo, no
weighting collisions: rank -> path is a bijection onto the first 2^64 ranks.

Fanout per state = number of greedily selected prefix-free *supported*
tokens (supported = attested in >=2 distinct training word types), capped at
`cap`. Only if that is below `floor` is the row topped up with global backoff
tokens of the same class (marked fallback). Tokens never come from outside the
learned vocabulary.
"""
import argparse
import gzip
import importlib.util
import json
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODELS = ROOT.parent
CORPORA = Path("/home/agent/corpora/readable-hash-overnight")
FORMAT = "dynphrase v1"
END = "$"


def trainer():
    spec = importlib.util.spec_from_file_location("readable_training_tokenizer", MODELS / "tokenize.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TRAINER = trainer()


def emitted(token):
    return token.removeprefix("^").removesuffix("$")


def token_class(token):
    if token.startswith("^"):
        return "B"
    if token.endswith("$"):
        return "E"
    return "M"


# ---------------------------------------------------------------- corpora

def load_words(source, language):
    """Return ({word: weight}, description). Weight is occurrences or 1."""
    if source == "unique":
        words = TRAINER.extract_words((MODELS / "training-data/english-lowercase.txt").read_text())
        return dict.fromkeys(words, 1)
    data = json.load(gzip.open(CORPORA / f"{language}_counts.json.gz", "rt", encoding="utf-8"))
    train = data["train"]
    if source == "fineweb-occ":
        return {word: value[0] for word, value in train.items()}
    if source == "fineweb-type":
        return dict.fromkeys(train, 1)
    raise ValueError(source)


def load_heldout(language):
    data = json.load(gzip.open(CORPORA / f"{language}_counts.json.gz", "rt", encoding="utf-8"))
    return {word: value[0] for word, value in data["heldout"].items()}


def vocabulary(language):
    if language == "en":
        tokens = json.loads((MODELS / "phrase_v3_model.json").read_text())["tokens"]
        return {token: index for index, token in enumerate(tokens)}, "v3 1024-token English vocabulary (unique-word trained)"
    words = list(json.load(gzip.open(CORPORA / f"{language}_counts.json.gz", "rt", encoding="utf-8"))["train"])
    words.sort()
    vocab = TRAINER.build_vocabulary(*TRAINER.collect_ngram_counts(words))
    vocab = {token: index for token, index in vocab.items() if not token.startswith("[UNUSED")}
    return vocab, f"1024-slot position vocabulary built by models/tokenize.py algorithm from {language} FineWeb2 train word types"


def transitions(words, vocab):
    """weight[(prev, next)], types[(prev, next)] with prev None for word start."""
    weight, types = Counter(), Counter()
    for word, count in words.items():
        tokens = TRAINER.tokenize_word(word, vocab)
        if len(tokens) < 2 or any(token not in vocab for token in tokens):
            continue
        for previous, following in zip([None] + tokens, tokens):
            weight[previous, following] += count
            types[previous, following] += 1
    return weight, types


# ---------------------------------------------------------------- grammar

def build(words, vocab, cap, floor, alphabet, max_tokens=4, min_types=2):
    weight, types = transitions(words, vocab)
    by_context = defaultdict(dict)
    global_weight = Counter()
    for (previous, following), value in weight.items():
        by_context[previous][following] = value
        global_weight[following] += value
    usable = [token for token in vocab if emitted(token) and set(emitted(token)) <= alphabet]
    classes = defaultdict(list)
    for token in usable:
        classes[token_class(token)].append(token)

    def eligible(slot):
        if slot == 0:
            return classes["B"]
        if slot == max_tokens - 1:
            return classes["E"]
        return classes["M"] + classes["E"]

    def row(slot, previous):
        local = by_context.get(previous, {})
        quality = sorted(eligible(slot), key=lambda token: (-local.get(token, 0), -global_weight[token], emitted(token)))
        chosen, texts = [], []
        for token in quality:
            if local.get(token, 0) == 0 or len(chosen) >= cap:
                break
            if types[previous, token] < min_types:
                continue
            text = emitted(token)
            if any(text.startswith(other) or other.startswith(text) for other in texts):
                continue
            chosen.append((token, False))
            texts.append(text)
        if len(chosen) < floor:
            backoff = sorted(eligible(slot), key=lambda token: (-global_weight[token], emitted(token)))
            for token in backoff:
                if len(chosen) >= floor:
                    break
                text = emitted(token)
                if any(text.startswith(other) or other.startswith(text) for other in texts):
                    continue
                chosen.append((token, True))
                texts.append(text)
        return chosen

    states, index, queue = [], {(0, None): 0}, [(0, None)]
    while queue:
        key = queue.pop(0)
        slot, previous = key
        choices = []
        for token, fallback in row(slot, previous):
            if token_class(token) == "E":
                target = END
            else:
                target = (slot + 1, token)
                if target not in index:
                    index[target] = len(index)
                    queue.append(target)
            choices.append({"token": token, "text": emitted(token), "next": target, "fallback": fallback,
                            "local": by_context.get(previous, {}).get(token, 0)})
        states.append({"key": key, "choices": choices})
    for state in states:
        for choice in state["choices"]:
            if choice["next"] != END:
                choice["next"] = index[choice["next"]]
    return states


class Codec:
    def __init__(self, states, words):
        self.states, self.words = states, words
        self.count = [0] * len(states)
        for position in range(len(states) - 1, -1, -1):
            self.count[position] = sum(self.sub(choice) for choice in states[position]["choices"])
        self.width = self.count[0]
        self.capacity = self.width ** words
        if self.capacity < 1 << 64:
            raise ValueError(f"insufficient: W={self.width} log2(W^{words})={_log2(self.capacity):.3f} < 64")

    def sub(self, choice):
        return 1 if choice["next"] == END else self.count[choice["next"]]

    def word(self, rank):
        state, text, path = 0, "", []
        while True:
            for choice in self.states[state]["choices"]:
                size = self.sub(choice)
                if rank < size:
                    break
                rank -= size
            text += choice["text"]
            path.append(choice)
            if choice["next"] == END:
                return text, path
            state = choice["next"]

    def encode(self, value):
        assert 0 <= value < 1 << 64
        digits = []
        for _ in range(self.words):
            value, digit = divmod(value, self.width)
            digits.append(digit)
        return " ".join(self.word(digit)[0] for digit in reversed(digits))

    def parse_word(self, text):
        state, rank = 0, 0
        while True:
            for choice in self.states[state]["choices"]:
                if text.startswith(choice["text"]):
                    break
                rank += self.sub(choice)
            else:
                return None
            text = text[len(choice["text"]):]
            if choice["next"] == END:
                return rank if text == "" else None
            state = choice["next"]

    def decode(self, phrase):
        parts = phrase.split(" ")
        if len(parts) != self.words:
            return None
        value = 0
        for part in parts:
            rank = self.parse_word(part)
            if rank is None:
                return None
            value = value * self.width + rank
        return value if value < 1 << 64 else None

    # exact statistics -------------------------------------------------
    def subtree_stats(self):
        """Per state: letters histogram and sums of per-path features."""
        stats = [None] * len(self.states)
        for position in range(len(self.states) - 1, -1, -1):
            hist, tokens, fallback, nonlocal_, heldout = Counter(), Counter(), 0, 0, 0
            for choice in self.states[position]["choices"]:
                self._accumulate(choice, stats, hist, tokens)
                child = (Counter({0: 1}), Counter({0: 1}), 0, 0, 0) if choice["next"] == END else stats[choice["next"]]
                size = self.sub(choice)
                fallback += child[2] + size * choice["fallback"]
                nonlocal_ += child[3] + size * (choice["local"] == 0)
                heldout += child[4] + size * (not choice.get("heldout", False))
            stats[position] = (hist, tokens, fallback, nonlocal_, heldout)
        return stats

    def _accumulate(self, choice, stats, hist, tokens):
        child = (Counter({0: 1}), Counter({0: 1})) if choice["next"] == END else stats[choice["next"]][:2]
        for letters, count in child[0].items():
            hist[letters + len(choice["text"])] += count
        for length, count in child[1].items():
            tokens[length + 1] += count


def letters_hist_prefix(codec, stats, limit):
    """Letter histogram and token histogram over word ranks [0, limit)."""
    hist, tokens = Counter(), Counter()

    def walk(state, letters, depth, limit):
        for choice in codec.states[state]["choices"]:
            if limit <= 0:
                return
            size = codec.sub(choice)
            take = min(size, limit)
            if take == size:
                child = (Counter({0: 1}), Counter({0: 1})) if choice["next"] == END else stats[choice["next"]][:2]
                for count_letters, count in child[0].items():
                    hist[letters + len(choice["text"]) + count_letters] += count
                for count_tokens, count in child[1].items():
                    tokens[depth + 1 + count_tokens] += count
            else:
                walk(choice["next"], letters + len(choice["text"]), depth + 1, take)
            limit -= take

    walk(0, 0, 0, limit)
    return hist, tokens


def word_weights(codec):
    """Exact number of u64 values mapping each rank class of each word.

    Returns list per word of [(limit, multiplicity)] meaning ranks [0,limit)
    each occur `multiplicity` times (stacked)."""
    total = 1 << 64
    result = []
    for position in range(codec.words):
        stride = codec.width ** (codec.words - 1 - position)  # value of one digit
        if position == 0:
            quotient, remainder = divmod(total, stride)
            # ranks < quotient occur `stride` times; rank == quotient occurs remainder times
            result.append([(quotient, stride - remainder), (quotient + 1, remainder)] if remainder else [(quotient, stride)])
        else:
            block = stride * codec.width
            full, remainder = divmod(total, block)
            # each full block contributes stride per rank; partial block contributes per rank
            spans = [(codec.width, full * stride)]
            quotient, rest = divmod(remainder, stride)
            if quotient and stride - rest:
                spans.append((quotient, stride - rest))
            if rest:
                spans.append((quotient + 1, rest))
            result.append(spans)
    return result


def exact_metrics(codec):
    stats = codec.subtree_stats()
    per_word = []
    phrase_letters = Fraction(0)
    weights = word_weights(codec)
    for spans in weights:
        hist, tokens = Counter(), Counter()
        for limit, multiplicity in spans:
            part_hist, part_tokens = letters_hist_prefix(codec, stats, limit)
            for key, value in part_hist.items():
                hist[key] += value * multiplicity
            for key, value in part_tokens.items():
                tokens[key] += value * multiplicity
        assert sum(hist.values()) == 1 << 64
        mean = Fraction(sum(key * value for key, value in hist.items()), 1 << 64)
        phrase_letters += mean
        per_word.append({
            "letters_min": min(hist), "letters_max": max(hist), "letters_mean": float(mean),
            "letters_hist": {str(key): value / (1 << 64) for key, value in sorted(hist.items())},
            "tokens_hist": {str(key): value / (1 << 64) for key, value in sorted(tokens.items())},
            "reachable_ranks": max(limit for limit, _ in spans),
        })
    root = stats[0]
    transitions = sum(key * value for key, value in root[1].items())
    return {
        "per_word_uniform_u64": per_word,
        "phrase_letters_mean_uniform_u64": float(phrase_letters),
        "full_grammar_transition_rates": {
            "fallback": root[2] / transitions,
            "nonlocal_train": root[3] / transitions,
            "not_attested_heldout": root[4] / transitions,
            "note": "over all W word paths equally (words 2..n are within 2^-40 of this under uniform u64)",
        },
    }


# ---------------------------------------------------------------- export

def export_text(states, name, words):
    lines = [FORMAT, f"name {name}", f"words {words}", f"states {len(states)}"]
    for state in states:
        lines.append(" ".join(f"{choice['text']}>{choice['next']}" for choice in state["choices"]))
    return "\n".join(lines) + "\n"


def branching(states):
    fanout = Counter(len(state["choices"]) for state in states)
    return {str(key): fanout[key] for key in sorted(fanout)}


ALPHABETS = {"en": set("abcdefghijklmnopqrstuvwxyz"), "tr": set("abcçdefgğhıijklmnoöprsştuüvyzâîû")}


def compile_arm(language, source, cap, floor=2, words=3, max_tokens=4, min_types=2):
    vocab, vocab_note = vocabulary(language)
    weights = load_words(source, language)
    states = build(weights, vocab, cap, floor, ALPHABETS[language], max_tokens, min_types)
    heldout_weight, _ = transitions(load_heldout(language), vocab)
    for state in states:
        previous = state["key"][1]
        for choice in state["choices"]:
            choice["heldout"] = heldout_weight[previous, choice["token"]] > 0
    codec = Codec(states, words)
    real = {}
    for label, vocabulary_words in (("train", weights), ("heldout", load_heldout(language))):
        hits = sum(1 for word in vocabulary_words if codec.parse_word(word) is not None)
        real[label] = {"vocabulary_words_that_are_complete_codewords": hits,
                       "fraction_of_word_codespace": hits / codec.width}
    choices = sum(len(state["choices"]) for state in states)
    report = {
        "language": language, "source": source, "cap": cap, "floor": floor, "words": words, "max_tokens": max_tokens, "min_types": min_types,
        "vocabulary": vocab_note, "training_word_types": len(weights),
        "states": len(states), "choices": choices, "branching_hist": branching(states),
        "fallback_choices": sum(choice["fallback"] for state in states for choice in state["choices"]),
        "word_width_W": codec.width, "capacity": str(codec.capacity),
        "log2_capacity": _log2(codec.capacity),
        "utilization_2^64_over_capacity": (1 << 64) / codec.capacity,
        "real_word_codewords": real,
    }
    report.update(exact_metrics(codec))
    return states, codec, report


def _log2(value):
    import math
    return math.log2(value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", default="en")
    parser.add_argument("--source", default="unique")
    parser.add_argument("--caps", default="16,32,64,128,256")
    parser.add_argument("--floor", type=int, default=2)
    parser.add_argument("--words", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=4)
    parser.add_argument("--min-types", type=int, default=2)
    parser.add_argument("--export", help="write model text for the single given cap to this path")
    parser.add_argument("--report", help="append sweep JSON here")
    args = parser.parse_args()
    reports = []
    for cap in map(int, args.caps.split(",")):
        try:
            states, codec, report = compile_arm(args.language, args.source, cap, args.floor, args.words, args.max_tokens, args.min_types)
        except ValueError as error:
            report = {"language": args.language, "source": args.source, "cap": cap, "words": args.words, "error": str(error)}
            states = None
        reports.append(report)
        print(json.dumps({key: report.get(key) for key in ("language", "source", "cap", "word_width_W", "log2_capacity",
                                                           "phrase_letters_mean_uniform_u64", "error")}))
        if args.export and states:
            Path(args.export).write_text(export_text(states, f"{args.language}-{args.source}-cap{cap}-t{args.max_tokens}-m{args.min_types}-w{args.words}", args.words), encoding="utf-8")
    if args.report:
        Path(args.report).write_text(json.dumps(reports, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
