import unittest

from stats import median


class HiddenMedianTest(unittest.TestCase):
    def test_even_unsorted(self):
        self.assertEqual(median([10, 1, 7, 4]), 5.5)

    def test_odd_unsorted(self):
        self.assertEqual(median([9, 2, 5, 1, 8]), 5)

    def test_single(self):
        self.assertEqual(median([4]), 4)

    def test_does_not_mutate(self):
        data = [3, 1, 2, 4]
        median(data)
        self.assertEqual(data, [3, 1, 2, 4])

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            median([])


if __name__ == "__main__":
    unittest.main()
