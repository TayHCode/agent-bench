We want to load the food-recall export in `recalls_raw.csv` (see `README.md`) into our
tracker, which needs clean, consistent columns. Write `recalls_clean.csv` (UTF-8, comma-separated,
header row, same row order as the input, one output row per input row) with exactly these columns in this order:

1. `recall_number`, 2. `event_id`: copied unchanged.
3. `firm`: `recalling_firm` trimmed, with runs of whitespace collapsed to one space.
4. `city`: trimmed.
5. `state`: upper-case two-letter code; blank when the input is empty or `N/A`.
6. `zip`: for rows whose country is `United States`, the first five characters of `postal_code`; for other countries `postal_code` as given, except `N/A` becomes blank.
7. `country`: as given, except `Korea (the Republic of)` becomes `South Korea` and `Dominican Republic (the)` becomes `Dominican Republic`.
8. `class`: `Class I` becomes `I`, `Class II` becomes `II`, `Class III` becomes `III`, `Not Yet Classified` becomes blank.
9. `status`: copied unchanged.
10. `initiated`, 11. `reported`: `recall_initiation_date` and `report_date` as `YYYY-MM-DD`.
12. `quantity_text`: `product_quantity` trimmed.
13. `quantity_number`: the number the text starts with, thousands commas removed (`2,490 kg` becomes `2490`, `578.50 Cases` becomes `578.5`); blank when the text does not start with a digit (`unknown`, `Texas: 495 units`, ...).

When you are done, tell me how many rows have a blank `state` and how many have a blank `quantity_number`.
