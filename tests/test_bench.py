import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from bench import percentile


class PercentileTest(unittest.TestCase):
    def test_interpolation_and_edge_cases(self):
        self.assertEqual(percentile([], .95), 0)
        self.assertEqual(percentile([4], .95), 4)
        self.assertAlmostEqual(percentile([1, 2, 3, 4, 5], .95), 4.8)


if __name__ == '__main__':
    unittest.main()
