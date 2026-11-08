#!/usr/bin/env python3
"""Measure v3/v4 exact reachable-path locality and length; regenerate report."""
import argparse
import json
import subprocess
from fractions import Fraction
from pathlib import Path
from reversible_tables import load_training_counts

ROOT = Path(__file__).resolve().parent


def word_stats(model, labels, counts):
    tokens = model['tokens']
    indices = {context: index for index, context in enumerate(model['contexts'])}
    def length(token):
        return len(tokens[token].removeprefix('^').removesuffix('$'))
    states = {token: (1, length(token), length(token), length(token)) for token in model['begin']}
    coverage = []
    for label in labels:
        following = {}
        local = total = 0
        for previous, (paths, length_sum, minimum, maximum) in states.items():
            observed = counts['end' if label.startswith('end') else 'middle'].get(previous, {})
            for token in model[label][indices[previous]]:
                total += paths
                local += paths * (token in observed)
                old_paths, old_sum, old_min, old_max = following.get(token, (0, 0, 10000, 0))
                token_length = length(token)
                following[token] = (old_paths + paths, old_sum + length_sum + paths * token_length, min(old_min, minimum + token_length), max(old_max, maximum + token_length))
        coverage.append({'table': label, 'local_paths': local, 'fallback_paths': total - local, 'total_paths': total, 'local_fraction': str(Fraction(local, total)), 'fallback_fraction': str(Fraction(total - local, total))})
        states = following
    paths = sum(state[0] for state in states.values())
    mean = Fraction(sum(state[1] for state in states.values()), paths)
    return {'paths': paths, 'min_letters': min(state[2] for state in states.values()), 'max_letters': max(state[3] for state in states.values()), 'mean_letters': str(mean), 'mean_letters_decimal': float(mean), 'coverage': coverage}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    model = json.loads((ROOT / 'phrase_v3_model.json').read_text())
    model['end16'] = json.loads((ROOT / 'phrase_v4_end16.json').read_text())['end16']
    counts = load_training_counts(ROOT / 'training-data/english-lowercase.txt', ROOT / 'training-data/english-lowercase-model.json')
    first = word_stats(model, ('middle32', 'middle32', 'end32'), counts)
    second = word_stats(model, ('middle32', 'middle16', 'end32'), counts)
    third = word_stats(model, ('middle32', 'middle32', 'end16'), counts)
    def phrase(last):
        words = [first, second, last]
        mean = sum((Fraction(word['mean_letters']) for word in words), Fraction())
        coverage = []
        for position in range(3):
            local = sum((Fraction(word['coverage'][position]['local_paths'], word['coverage'][position]['total_paths']) for word in words), Fraction()) / 3
            coverage.append({'position': ('first_middle', 'second_middle', 'end')[position], 'local_fraction': str(local), 'fallback_fraction': str(1 - local), 'local_probability': float(local), 'fallback_probability': float(1 - local)})
        return {'word1': first, 'word2': second, 'word3': last, 'phrase_min_letters': sum(word['min_letters'] for word in words), 'phrase_max_letters': sum(word['max_letters'] for word in words), 'phrase_mean_letters': str(mean), 'phrase_mean_letters_decimal': float(mean), 'coverage_per_transition_position': coverage, 'spaces': 2}
    output = subprocess.check_output(['cargo', 'run', '--quiet', '--example', 'phrase_v4_comparison'], cwd=ROOT.parent, text=True)
    examples = [dict(zip(('input', 'u64', 'v3', 'v4'), line.split('\t'))) for line in output.splitlines()]
    report = {'corpus_unique_words': counts['word_count'], 'method': 'uniform u64; exact reachable-path-weighted observed adjacency and fallback from unique-word corpus, not running-text frequencies', 'v3': phrase(second), 'v4': phrase(third), 'examples': examples}
    result = json.dumps(report, indent=2, sort_keys=True) + '\n'
    path = ROOT / 'phrase_v4_comparison.json'
    if args.check:
        if path.read_text() != result:
            raise SystemExit(f'generated file differs: {path}')
    else:
        path.write_text(result)
    print(result)


if __name__ == '__main__':
    main()
