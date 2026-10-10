"""`agentbench check-files ACTUAL EXPECTED`: the stock comparer for data tasks (csv, json, text).

Counts wrong rows (csv, or a json list of objects with --key), wrong values (other json) or differing lines (text);
exits 0 when the count is at most --max-wrong. Numbers compare as numbers (1.0 equals 1), text is trimmed.
No model is involved. Odd rules still deserve their own check.py.
"""

import csv
import difflib
import json
from pathlib import Path


def _norm(v):
    if isinstance(v, str):
        v = v.strip()
        try:
            return float(v)
        except ValueError:
            return v
    if isinstance(v, bool) or v is None:
        return v
    return float(v) if isinstance(v, (int, float)) else v


def _rows_wrong(actual, expected, key, notes):
    """actual, expected: lists of dicts. Returns wrong-row count."""
    if key:
        cols = [k.strip() for k in key.split(",")]
        def k_of(r):
            return tuple(str(r.get(c, "")).strip() for c in cols)
        a, wrong = {}, 0
        for r in actual:
            if k_of(r) in a:
                wrong += 1
                notes.append(f"duplicate key {k_of(r)}")
            a[k_of(r)] = r
        e = {k_of(r): r for r in expected}
        for k, er in e.items():
            if k not in a:
                wrong += 1
                notes.append(f"missing row {k}")
            elif {c: _norm(v) for c, v in a[k].items()} != {c: _norm(v) for c, v in er.items()}:
                wrong += 1
                bad = [c for c in er if _norm(a[k].get(c)) != _norm(er[c])]
                notes.append(f"row {k} differs in {bad}")
        extra = [k for k in a if k not in e]
        wrong += len(extra)
        notes += [f"unexpected row {k}" for k in extra]
        return wrong
    wrong = abs(len(actual) - len(expected))
    if wrong:
        notes.append(f"{len(actual)} rows, expected {len(expected)}")
    for i, (ar, er) in enumerate(zip(actual, expected), 1):
        if {c: _norm(v) for c, v in ar.items()} != {c: _norm(v) for c, v in er.items()}:
            wrong += 1
            notes.append(f"row {i} differs")
    return wrong


def _leaves_wrong(a, e, path, notes):
    if isinstance(e, dict) and isinstance(a, dict):
        return sum(_leaves_wrong(a.get(k), e.get(k), f"{path}.{k}", notes) for k in set(a) | set(e))
    if isinstance(e, list) and isinstance(a, list):
        wrong = abs(len(a) - len(e))
        if wrong:
            notes.append(f"{path or 'top level'}: {len(a)} items, expected {len(e)}")
        return wrong + sum(_leaves_wrong(x, y, f"{path}[{i}]", notes) for i, (x, y) in enumerate(zip(a, e)))
    if _norm(a) != _norm(e):
        notes.append(f"{path or 'value'} differs")
        return 1
    return 0


def compare(actual, expected, fmt=None, key=None):
    """-> (wrong, total, notes). Raises ValueError for unreadable input."""
    actual, expected = Path(actual), Path(expected)
    fmt = fmt or {".csv": "csv", ".json": "json"}.get(expected.suffix.lower(), "text")
    notes = []
    if fmt == "csv":
        def read(p):
            with open(p, newline="", encoding="utf-8-sig") as f:
                r = csv.DictReader(f)
                return list(r), r.fieldnames or []
        (arows, ahead), (erows, ehead) = read(actual), read(expected)
        if sorted(ahead) != sorted(ehead):
            return len(erows), len(erows), [f"columns {ahead} do not match the expected {ehead}"]
        return _rows_wrong(arows, erows, key, notes), len(erows), notes
    if fmt == "json":
        a, e = json.loads(actual.read_text()), json.loads(expected.read_text())
        if key and isinstance(a, list) and isinstance(e, list) and all(isinstance(x, dict) for x in a + e):
            return _rows_wrong(a, e, key, notes), len(e), notes
        wrong = _leaves_wrong(a, e, "", notes)
        return wrong, max(len(e) if isinstance(e, (list, dict)) else 1, 1), notes
    if fmt == "text":
        al = [l.rstrip() for l in actual.read_text().splitlines()]
        el = [l.rstrip() for l in expected.read_text().splitlines()]
        wrong = 0
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, el, al, autojunk=False).get_opcodes():
            if tag != "equal":
                wrong += max(i2 - i1, j2 - j1)
                notes.append(f"lines {i1 + 1}-{i2} differ")
        return wrong, len(el), notes
    raise ValueError(f"unknown format {fmt!r}")


def main(actual, expected, fmt=None, key=None, max_wrong=0):
    if not Path(actual).is_file():
        print(f"check-files: the output file {Path(actual).name!r} does not exist")
        return 1
    try:
        wrong, total, notes = compare(actual, expected, fmt, key)
    except (ValueError, OSError, UnicodeDecodeError, csv.Error) as e:
        print(f"check-files: cannot compare: {e}")
        return 1
    print(f"check-files: {wrong} wrong of {total} (allowed {max_wrong})")
    for n in notes[:5]:
        print("  " + n)
    return 0 if wrong <= max_wrong else 1
