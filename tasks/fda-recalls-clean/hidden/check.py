"""Hidden check for fda-recalls-clean: recalls_clean.csv must equal the known answer cell for cell."""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
out = Path("recalls_clean.csv")
if not out.exists():
    print("recalls_clean.csv not found")
    sys.exit(1)


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r, [])
        return header, [row for row in r]


eh, erows = load(HERE / "expected_clean.csv")
gh, grows = load(out)
problems = []
if gh != eh:
    problems.append(f"header {gh} != {eh}")
if len(grows) != len(erows):
    problems.append(f"{len(grows)} rows, expected {len(erows)}")
if not problems:
    qn = eh.index("quantity_number")
    for i, (g, e) in enumerate(zip(grows, erows), start=2):
        if len(g) != len(e):
            problems.append(f"line {i}: {len(g)} cells, expected {len(e)}")
            continue
        for j, (a, b) in enumerate(zip(g, e)):
            if j == qn and a and b:
                try:
                    if float(a) == float(b):
                        continue
                except ValueError:
                    pass
            if a != b:
                problems.append(f"line {i} {eh[j]}: {a!r} != {b!r}")
print(f"{len(problems)} problem(s)")
print("\n".join(problems[:15]))
sys.exit(1 if problems else 0)
