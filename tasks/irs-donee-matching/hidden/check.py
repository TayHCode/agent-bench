"""Hidden check for irs-donee-matching: matched.csv against the known answer, at most 3 wrong rows.

A row is wrong when any cell differs from the expected row. The one tolerance: for a `many` row (several organizations
share the name) a guessed EIN is accepted when it is the true one and the row says `one`; the other cells of such a row
are not judged.
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAX_WRONG = 3
out = Path("matched.csv")
if not out.exists():
    print("matched.csv not found")
    sys.exit(1)


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r, [])
        return header, [row for row in r]


eh, erows = load(HERE / "expected_matched.csv")
gh, grows = load(out)
exp_header = eh[:10]
if gh != exp_header:
    print(f"header {gh} != {exp_header}")
    sys.exit(1)
if len(grows) != len(erows):
    print(f"{len(grows)} rows, expected {len(erows)}")
    sys.exit(1)
wrong = []
for i, (g, e) in enumerate(zip(grows, erows), start=2):
    true_ein, e = e[10], e[:10]
    if g == e:
        continue
    if e[4] == "many" and len(g) == 10 and g[3] == true_ein and g[4] == "one":  # told not to guess, but guessed right
        continue
    wrong.append((i, e[0], e[4], g[3:5], e[3:5] if e[4] != "one" else e[3:]))
print(f"{len(wrong)} wrong row(s) of {len(erows)} (allowed {MAX_WRONG})")
for w in wrong[:12]:
    print(f"line {w[0]} {w[1]!r} expected match={w[2]}: got {w[3]}, expected {w[4]}")
sys.exit(1 if len(wrong) > MAX_WRONG else 0)
