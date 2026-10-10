# Food recall export

`recalls_raw.csv` is an export of FDA food enforcement reports (openFDA, reports dated
2026-07-01 to 2026-10-08), one row per recalled product, in the order the API returned them.
Public-domain data (CC0).

Entity labels overlapping private terms have consistent neutral aliases in this export; record IDs, dates and numerical fields are retained.

| column | meaning |
|---|---|
| recall_number, event_id | identifiers |
| recalling_firm, city, state, postal_code, country | who and where |
| classification | `Class I`, `Class II`, `Class III` or `Not Yet Classified` |
| status | `Ongoing`, `Completed`, `Terminated` |
| recall_initiation_date, report_date | `YYYYMMDD` |
| product_quantity | free text as typed by the FDA reviewer |
