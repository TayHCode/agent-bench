# County employment reconciliation inputs

Unmodified BLS QCEW quarterly singlefile ZIPs: 2025 and 2026, vintage downloaded
2026-10-10. The 2026 first-quarter release was published 2026-08-28. These archives
contain about 2.67 GB of decompressed CSV, across all geographic, ownership and
industry levels. CSV files have header rows and blank lines. The source data
have not been manufactured, reordered, corrupted or stripped of needed fields.

Source and field definitions:
https://www.bls.gov/cew/downloadable-data-files.htm
https://www.bls.gov/cew/about-data/downloadable-file-layouts/quarterly/naics-based-quarterly-layout.htm

Aggregation codes: county private totals 71, county ownership/NAICS sector 74;
national private totals 11, national ownership/NAICS sector 14. Use size code 0,
ownership code 5. Non-disclosure is `N`, not a numeric zero. County codes ending
000 are state totals; 999 denotes an unknown county. US000 is the national total.
Only 50 states and DC are in the requested county output (no territories).

Deliverables in the repository root (UTF-8 CSV with headers; any row order; unique keys):

`sector_shift_share.csv`:
area_fips,industry_code,status,employment_2025,employment_2026,change,national_share,industry_mix,regional_shift,lq_2026,weekly_wage_2025,weekly_wage_2026,wage_growth_pct

`county_summary.csv`:
area_fips,employment_2025,employment_2026,change,covered_employment_2025,covered_employment_2026,covered_change,national_share,industry_mix,regional_shift,unallocated_change,ok_sectors,unavailable_sectors

County employment and change are the published all-industry figures (or blank
if withheld/missing). Covered employment/change sums only the `ok` sector pairs.
The unallocated change is published total change minus covered change.
The contributions are employment amounts, not percentage points.
`unavailable_sectors` counts all non-`ok` pairs in that county's union of sectors.
BLS data are public domain. Source: U.S. Bureau of Labor Statistics.
