import json
import unittest
from pathlib import Path
from compile_phrase import CONTEXTS, emitted, prefix_free, valid, validate
from compile_phrase_v4 import compile_rows
from compare_phrase_v4 import word_stats
from reversible_tables import load_training_counts

ROOT = Path(__file__).resolve().parent


class PhraseV4Tests(unittest.TestCase):
    def test_frozen_tables_and_regeneration(self):
        model = json.loads((ROOT / 'phrase_v3_model.json').read_text())
        validate(model)
        stored = json.loads((ROOT / 'phrase_v4_end16.json').read_text())
        rows, omissions = compile_rows()
        self.assertEqual(stored, {'contexts': CONTEXTS, 'end16': rows, 'omitted_local_tokens_by_context_id': omissions})
        self.assertEqual(len(rows), 768)
        for row in rows:
            self.assertEqual(len(row), 16)
            self.assertTrue(all(256 <= token < 512 and valid(emitted(model['tokens'][token])) for token in row))
            self.assertTrue(prefix_free([emitted(model['tokens'][token]) for token in row]))
        self.assertEqual(128 * 32 * 32 * 32, 1 << 22)
        self.assertEqual(128 * 32 * 16 * 32, 1 << 21)
        self.assertEqual(128 * 32 * 32 * 16, 1 << 21)

    def test_report_agrees_with_legacy_measurement_and_compiler(self):
        report = json.loads((ROOT / 'phrase_v4_comparison.json').read_text())
        previous = json.loads((ROOT / 'phrase_comparison.json').read_text())['v3']
        self.assertEqual(report['v3']['phrase_mean_letters'], previous['phrase_mean_letters'])
        for field in ('phrase_min_letters', 'phrase_max_letters'):
            self.assertEqual(report['v3'][field], previous[field])
        for word, old_word in (('word1', 'word1'), ('word2', 'word2_and_3'), ('word3', 'word2_and_3')):
            for actual, expected in zip(report['v3'][word]['coverage'], previous[old_word]['coverage_first_middle_second_middle_end']):
                self.assertEqual(actual['local_paths'], expected['local_paths'])
                self.assertEqual(actual['total_paths'], expected['total_paths'])
        model = json.loads((ROOT / 'phrase_v3_model.json').read_text())
        model['end16'] = json.loads((ROOT / 'phrase_v4_end16.json').read_text())['end16']
        counts = load_training_counts(ROOT / 'training-data/english-lowercase.txt', ROOT / 'training-data/english-lowercase-model.json')
        self.assertEqual(report['v4']['word3'], word_stats(model, ('middle32', 'middle32', 'end16'), counts))
        self.assertEqual(report['v4']['word1'], report['v3']['word1'])
        self.assertEqual(report['v4']['word2'], report['v3']['word2'])


if __name__ == '__main__':
    unittest.main()
