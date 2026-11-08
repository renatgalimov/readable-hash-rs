import json
import unittest
from pathlib import Path
from compile_phrase import validate

ROOT = Path(__file__).resolve().parent

class RevisedPhraseTests(unittest.TestCase):
    def test_tables_and_allocation(self):
        model = json.loads((ROOT / 'phrase_v3_model.json').read_text())
        validate(model)
        self.assertEqual(128 * 32 * 32 * 32, 1 << 22)
        self.assertEqual(128 * 32 * 16 * 32, 1 << 21)

    def test_independent_report_agrees_with_compiler(self):
        comparison = json.loads((ROOT / 'phrase_comparison.json').read_text())
        for version, filename in (('v2', 'phrase_report.json'), ('v3', 'phrase_v3_report.json')):
            statistics = json.loads((ROOT / filename).read_text())['statistics']
            measured = comparison[version]
            for field in ('phrase_min_letters', 'phrase_max_letters', 'spaces'):
                self.assertEqual(statistics[field], measured[field])
            self.assertEqual(statistics['phrase_mean_letters'], measured['phrase_mean_letters_decimal'])
            for word in ('word1', 'word2_and_3'):
                for source, independent in zip(statistics[word]['coverage'].values(), measured[word]['coverage_first_middle_second_middle_end']):
                    self.assertEqual(source['local_paths'], independent['local_paths'])
                    self.assertEqual(source['all_paths'], independent['total_paths'])

if __name__ == '__main__':
    unittest.main()
