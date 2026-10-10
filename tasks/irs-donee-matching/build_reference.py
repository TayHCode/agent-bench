"""Build donees.csv, the known answer and the check's truth table for irs-donee-matching.

Run: python3 -I build_reference.py <task dir>      (reads build/pub78_new_england.txt and repo/eo_*.csv, repo/revocations_subset.txt)

The donee list is a seeded sample of Publication 78 rows (name, city, state; the EIN is the withheld truth), enriched with the
cases that make matching hard: names the BMF stores with a lost space where it wrapped the name over two fields, organizations
with a revocation record, same-name organizations in one city, and organizations that are not in the BMF extracts at all.
Matching key (the definition of "same organization"): upper-case letters and digits only, for name, city and state.
"""
import csv
import datetime
import random
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
repo = root / "repo"
rng = random.Random(20261010)
STATES = {"CT", "ME", "NH", "RI", "VT"}


def alnum(text):
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def spaced(text):
    return " ".join(re.sub(r"[^A-Z0-9 ]", " ", text.upper().replace("&", " AND ")).split())


def day(text):
    return datetime.datetime.strptime(text.strip().title(), "%d-%b-%Y").date()


pub = [l.split("|") for l in open(root / "build/pub78_new_england.txt", encoding="latin-1", newline="").read().split("\r\n") if l.strip()]
pub = [r for r in pub if r[3] in STATES]
bmf = {}
for s in ("ct", "me", "nh", "ri", "vt"):
    with open(repo / f"eo_{s}.csv", encoding="latin-1", newline="") as f:
        for r in csv.DictReader(f):
            bmf[r["EIN"]] = r
index = {}
for e, r in bmf.items():
    index.setdefault((alnum(r["NAME"]), alnum(r["CITY"]), r["STATE"]), []).append(e)
revs = {}
for line in open(repo / "revocations_subset.txt", encoding="latin-1", newline="").read().split("\r\n"):
    if line.strip():
        f = line.split("|")
        revs.setdefault(f[0], []).append(f)


def revocation(ein):
    rows = revs.get(ein)
    if not rows:
        return "N", ""
    last = max(rows, key=lambda r: (day(r[9]), bool(r[11].strip())))
    if last[11].strip() and day(last[11]) >= day(last[9]):
        return "N", ""
    return "Y", day(last[9]).isoformat()


def key(r):
    return (alnum(r[1]), alnum(r[2]), r[3])


matchable, absent = [], []
for r in pub:
    if r[0] not in bmf:
        if not index.get(key(r)):  # nobody in the extracts goes by this name in this city: a clean "none"
            absent.append(r)
    elif r[0] in index.get(key(r), []):
        matchable.append(r)
unique = [r for r in matchable if len(index[key(r)]) == 1]
many = [r for r in matchable if len(index[key(r)]) > 1]
wrap = [r for r in unique if spaced(r[1]) != spaced(bmf[r[0]]["NAME"]) and alnum(r[1]) == alnum(bmf[r[0]]["NAME"])]
revoked_related = [r for r in unique if r[0] in revs]
chosen = {}
for group, n in ((wrap, 60), (revoked_related, 150), (many, 40), (absent, 12), (unique, 450)):
    for r in rng.sample(group, min(n, len(group))):
        chosen.setdefault(r[0], r)
rows = list(chosen.values())
rng.shuffle(rows)

header = ["name", "city", "state", "ein", "match", "ntee", "ruling", "assets_usd", "revoked", "revoked_on"]
out, truth = [], []
for r in rows:
    k = key(r)
    cands = index.get(k, [])
    if not cands:
        exp = [r[1], r[2], r[3], "", "none", "", "", "", "", ""]
    elif len(cands) > 1:
        exp = [r[1], r[2], r[3], "", "many", "", "", "", "", ""]
    else:
        b = bmf[r[0]]
        rv, rv_on = revocation(r[0])
        ruling = f"{b['RULING'][:4]}-{b['RULING'][4:6]}" if b["RULING"].strip() else ""
        assets = str(int(b["ASSET_AMT"])) if b["ASSET_AMT"].strip() else ""
        exp = [r[1], r[2], r[3], f"{r[0][:2]}-{r[0][2:]}", "one", b["NTEE_CD"], ruling, assets, rv, rv_on]
    out.append(exp)
    truth.append(exp + [f"{r[0][:2]}-{r[0][2:]}"])

(root / "gold").mkdir(exist_ok=True)
(root / "hidden").mkdir(exist_ok=True)
with open(repo / "donees.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["name", "city", "state"])
    w.writerows([[e[0], e[1], e[2]] for e in out])
for dest, data, hdr in ((root / "gold/matched.csv", out, header), (root / "hidden/expected_matched.csv", truth, header + ["true_ein"])):
    with open(dest, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(hdr)
        w.writerows(data)
from collections import Counter
print(len(out), "rows", dict(Counter(e[4] for e in out)), "revoked Y:", sum(1 for e in out if e[8] == "Y"),
      "wrap:", sum(1 for r in rows if r in wrap))
