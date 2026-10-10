Bug report: `stats.median([1, 3, 2, 4])` returns 3 but should return 2.5.

Please fix `median` in `stats.py` so it is correct for even-length lists and for
unsorted input, without modifying the list passed in. An empty list should raise
`ValueError`. Run the tests in this folder (`python3 -m unittest`) when you are done.
