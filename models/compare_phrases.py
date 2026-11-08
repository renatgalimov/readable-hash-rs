#!/usr/bin/env python3
"""Independently evaluate frozen tables and regenerate the comparison report."""
import json
import subprocess
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from reversible_tables import load_training_counts

ROOT = Path(__file__).resolve().parent
counts = load_training_counts(ROOT / 'training-data/english-lowercase.txt', ROOT / 'training-data/english-lowercase-model.json')

def measure(model, labels):
    tokens = model['tokens']
    indices = {token: index for index, token in enumerate(model['contexts'])}
    length = lambda token: len(tokens[token].removeprefix('^').removesuffix('$'))
    def word(second):
        states = {token: (1, length(token), length(token), length(token)) for token in model['begin']}
        coverage = []
        for label in (labels[0], second, labels[2]):
            next_states = {}
            local = total = 0
            for previous, (paths, length_sum, minimum, maximum) in states.items():
                observed = counts['end' if label.startswith('end') else 'middle'].get(previous, {})
                for token in model[label][indices[previous]]:
                    total += paths
                    if token in observed:
                        local += paths
                    old_paths, old_sum, old_min, old_max = next_states.get(token, (0, 0, 10000, 0))
                    token_length = length(token)
                    next_states[token] = (old_paths + paths, old_sum + length_sum + paths * token_length, min(old_min, minimum + token_length), max(old_max, maximum + token_length))
            coverage.append({'local_paths': local, 'fallback_paths': total - local, 'total_paths': total, 'local_probability': str(Fraction(local, total)), 'fallback_probability': str(Fraction(total - local, total))})
            states = next_states
        paths = sum(state[0] for state in states.values())
        mean = Fraction(sum(state[1] for state in states.values()), paths)
        return {'paths': paths, 'min_letters': min(state[2] for state in states.values()), 'max_letters': max(state[3] for state in states.values()), 'mean_letters': str(mean), 'coverage_first_middle_second_middle_end': coverage}
    first, other = word(labels[0]), word(labels[1])
    mean = Fraction(first['mean_letters']) + 2 * Fraction(other['mean_letters'])
    return {'word1': first, 'word2_and_3': other, 'phrase_min_letters': first['min_letters'] + 2 * other['min_letters'], 'phrase_max_letters': first['max_letters'] + 2 * other['max_letters'], 'phrase_mean_letters': str(mean), 'phrase_mean_letters_decimal': float(mean), 'spaces': 2}

baseline = json.loads((ROOT / 'phrase_model.json').read_text())
revised = json.loads((ROOT / 'phrase_v3_model.json').read_text())
examples = subprocess.check_output(['cargo', 'run', '--quiet', '--example', 'phrase_comparison'], cwd=ROOT.parent, text=True)
rows = [dict(zip(('input', 'u64', 'v2', 'v3'), line.split('\t'))) for line in examples.splitlines()]
report = {'corpus_unique_words': counts['word_count'], 'method': 'uniform u64, exact reachable-path counts; observed adjacency from checked-in unique-word corpus, not running-text frequency', 'v2': measure(baseline, ('middle16', 'middle8', 'end128')), 'v3': measure(revised, ('middle32', 'middle16', 'end32')), 'beginning_ids_only_v2': sorted(set(baseline['begin']) - set(revised['begin'])), 'beginning_ids_only_v3': sorted(set(revised['begin']) - set(baseline['begin'])), 'examples': rows}
(ROOT / 'phrase_comparison.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps(report, indent=2))
