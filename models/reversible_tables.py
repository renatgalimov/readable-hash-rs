"""Deterministic prefix-free table selection for reversible word models."""


def load_training_counts(corpus_path, model_path):
    """Recreate unquantized transition counts with the checked-in tokenizer."""
    import importlib.util
    import json
    from collections import Counter, defaultdict
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("readable_training_tokenizer", Path(__file__).with_name("tokenize.py"))
    trainer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trainer)
    model = json.loads(model_path.read_text(encoding="utf-8"))
    words = trainer.extract_words(corpus_path.read_text(encoding="utf-8"))
    vocabulary = trainer.build_vocabulary(*trainer.collect_ngram_counts(words))
    if vocabulary != model["vocab"] or len(words) != model["total_words"]:
        raise ValueError("corpus does not match checked-in model")
    beginning = Counter()
    middle = defaultdict(Counter)
    ending = defaultdict(Counter)
    for word in words:
        tokens = trainer.tokenize_word(word, vocabulary)
        try:
            ids = [vocabulary[token] for token in tokens]
        except KeyError:
            continue
        if not ids:
            continue
        beginning[ids[0]] += 1
        for previous, following in zip(ids, ids[1:]):
            target = ending if 256 <= following < 512 else middle
            target[previous][following] += 1
    if (trainer.build_cumulative_list(beginning) != model["begin_transitions"]
            or trainer.build_cumulative_transitions(middle) != model["transitions"]
            or trainer.build_cumulative_transitions(ending) != model["end_transitions"]):
        raise ValueError("corpus transitions do not match checked-in model")
    return {"word_count": len(words), "begin": beginning, "middle": middle, "end": ending}


def choose_prefix_free(candidates, cardinality):
    """Maximize (local weight, global weight), then minimize token tuple."""
    trie = {}
    for text, weights in candidates.items():
        if not text or not text.isascii() or not text.isalpha() or not text.islower():
            raise ValueError("tokens must be nonempty lowercase ASCII")
        node = trie
        for character in text:
            node = node.setdefault(character, {})
        node[None] = (text, weights)

    def better(first, second):
        if second is None or first[:2] > second[:2]:
            return first
        if first[:2] == second[:2] and first[2] < second[2]:
            return first
        return second

    def solve(node):
        result = {0: (0, 0, ())}
        for character in sorted(key for key in node if key is not None):
            child = solve(node[character])
            combined = {}
            for left_count, left in result.items():
                for right_count, right in child.items():
                    count = left_count + right_count
                    if count <= cardinality:
                        option = (left[0] + right[0], left[1] + right[1], left[2] + right[2])
                        combined[count] = better(option, combined.get(count))
            result = combined
        if None in node and cardinality >= 1:
            text, weights = node[None]
            option = (weights[0], weights[1], (text,))
            result[1] = better(option, result.get(1))
        return result

    solution = solve(trie).get(cardinality)
    if solution is None:
        raise ValueError("insufficient prefix-free capacity")
    return solution[2]
