"""Builds repo/recalls_raw.csv from the saved openFDA response and the known-answer CSV.

Not shipped to contestants (only repo/ is). Usage: build_reference.py <openfda-response.json>
"""
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW_COLS = ["recall_number", "event_id", "recalling_firm", "city", "state", "postal_code", "country",
            "classification", "status", "recall_initiation_date", "report_date", "product_quantity"]
CLEAN_COLS = ["recall_number", "event_id", "firm", "city", "state", "zip", "country", "class", "status",
              "initiated", "reported", "quantity_text", "quantity_number"]
COUNTRY = {"Korea (the Republic of)": "South Korea", "Dominican Republic (the)": "Dominican Republic"}


def iso(d):
    return f"{d[:4]}-{d[4:6]}-{d[6:]}"


def clean_row(r):
    state = r["state"].strip()
    state = "" if state.upper() == "N/A" else state.upper()
    postal = r["postal_code"].strip()
    if postal.upper() == "N/A":
        postal = ""
    elif r["country"].strip() == "United States":
        postal = postal[:5]
    cls = r["classification"].strip()
    cls = "" if cls == "Not Yet Classified" else cls.removeprefix("Class ")
    qty = r["product_quantity"].strip()
    m = re.match(r"\d[\d,]*(\.\d+)?", qty)
    num = ""
    if m:
        val = float(m.group(0).replace(",", ""))
        num = str(int(val)) if val == int(val) else str(val)
    country = r["country"].strip()
    return {"recall_number": r["recall_number"], "event_id": r["event_id"],
            "firm": " ".join(r["recalling_firm"].split()), "city": r["city"].strip(), "state": state,
            "zip": postal, "country": COUNTRY.get(country, country), "class": cls, "status": r["status"].strip(),
            "initiated": iso(r["recall_initiation_date"]), "reported": iso(r["report_date"]),
            "quantity_text": qty, "quantity_number": num}


def write(path, cols, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    results = json.loads(Path(sys.argv[1]).read_text())["results"]
    raw = [{c: x.get(c, "") for c in RAW_COLS} for x in results]
    write(HERE / "repo" / "recalls_raw.csv", RAW_COLS, raw)
    clean = [clean_row(r) for r in raw]
    write(HERE / "gold" / "recalls_clean.csv", CLEAN_COLS, clean)
    write(HERE / "hidden" / "expected_clean.csv", CLEAN_COLS, clean)
    print(len(raw), "rows")
