"""Generate a small git repo with a deliberate bug and a later commit that fixes it, with a test.

Used by `agentbench demo`, the tests and the real-machine runs (python3 -m agentbench.toy DIR prints the fix commit's SHA).
Standard library only, so it runs on any machine that has python3 and git.
"""

import os
import subprocess
import sys
from pathlib import Path

CART_BUGGY = '''def total(prices, discount=0):
    """Sum of prices minus a percentage discount, rounded to cents."""
    return round(sum(prices) * (1 - discount / 100), 2)
'''
CART_FIXED = '''def total(prices, discount=0):
    """Sum of prices minus a percentage discount, rounded to cents. No prices (None or empty) is 0."""
    return round(sum(prices or []) * (1 - discount / 100), 2)
'''
TEST_OLD = '''import unittest

from cart import total


class CartTest(unittest.TestCase):
    def test_sum(self):
        self.assertEqual(total([1.5, 2.5]), 4.0)

    def test_discount(self):
        self.assertEqual(total([10, 10], discount=25), 15.0)
'''
PROMPT = ("`cart.total(None)` raises TypeError, but a cart with no prices should add up to 0. "
          "Fix it, and run the tests in tests/ before you finish.\n")
TEST_NEW = TEST_OLD + '''
    def test_none_means_no_prices(self):
        self.assertEqual(total(None), 0)
'''


def _git(repo, *args):
    env = os.environ | {"GIT_AUTHOR_NAME": "toy", "GIT_AUTHOR_EMAIL": "toy",
                        "GIT_COMMITTER_NAME": "toy", "GIT_COMMITTER_EMAIL": "toy"}
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, env=env).stdout.strip()


def make_toy(repo, extra_files=None):
    """Create the repo at `repo`; returns the SHA of the fix commit. extra_files: {path: text} added in the first commit."""
    repo = Path(repo)
    (repo / "tests").mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    (repo / "cart.py").write_text(CART_BUGGY)
    (repo / "tests" / "test_cart.py").write_text(TEST_OLD)
    (repo / "README.md").write_text("# toy cart\n")
    for rel, text in (extra_files or {}).items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "Add cart total")
    (repo / "cart.py").write_text(CART_FIXED)
    (repo / "tests" / "test_cart.py").write_text(TEST_NEW)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "total() crashes on an empty cart\n\nA cart with no prices arrives as None from the "
         "checkout page, and total(None) raises TypeError. It should be 0.\n\nSigned-off-by: Toy <toy>")
    return _git(repo, "rev-parse", "HEAD")


if __name__ == "__main__":
    print(make_toy(sys.argv[1]))
