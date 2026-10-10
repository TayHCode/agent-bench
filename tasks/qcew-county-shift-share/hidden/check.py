"""Compare every output cell and key to independently reconstructed known answers."""
import csv
import math
from pathlib import Path
import sys


def check(name):
    expected_path = Path(__file__).parent / name
    actual_path = Path(name)
    if not actual_path.is_file():
        return [f'{name}: missing output']
    with expected_path.open(newline='',encoding='utf-8') as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        expected = list(reader)
    with actual_path.open(newline='',encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != columns:
            return [f'{name}: wrong columns']
        actual = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in actual):
        return [f'{name}: malformed CSV row']
    keycols = ['area_fips','industry_code'] if 'industry_code' in columns else ['area_fips']
    def key(row):return tuple(row[k] for k in keycols)
    indexed = {key(row):row for row in actual}
    if len(indexed) != len(actual):return [f'{name}: duplicate keys']
    if set(indexed) != {key(row) for row in expected}:return [f'{name}: missing or extra keys']
    wrong = []
    for row in expected:
        got = indexed[key(row)]
        for column,want in row.items():
            value = got[column]
            if column in keycols or column == 'status' or want == '':
                ok = value == want
            else:
                try:
                    number = float(value)
                    ok = math.isfinite(number) and abs(number-float(want)) <= 0.00002
                except (ValueError,TypeError):ok = False
            if not ok:
                wrong.append((key(row),column))
                break
    return [f'{name}: {len(wrong)} incorrect rows; first {wrong[:5]}'] if wrong else []


if __name__ == '__main__':
    errors = check('sector_shift_share.csv') + check('county_summary.csv')
    print('\n'.join(errors) if errors else 'Both complete BLS outputs match the known answer.')
    sys.exit(bool(errors))
