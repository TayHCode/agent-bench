# IRS exempt-organization extracts, New England

Files in this folder. The IRS files were downloaded from irs.gov. Entity labels overlapping private terms have consistent neutral aliases; IDs, dates and numerical fields are retained. The revocation file is cut down to
the rows for organizations in the BMF extracts, retaining the original delimiters and blank lines at the top.

| File | What it is |
|---|---|
| `donees.csv` | Our list of organizations we have given to: `name`, `city`, `state`. The names come from IRS Publication 78, which writes them in mixed case. No EINs. |
| `eo_ct.csv`, `eo_me.csv`, `eo_nh.csv`, `eo_ri.csv`, `eo_vt.csv` | IRS Exempt Organizations Business Master File (EO BMF), one extract per state, one row per organization. Comma separated, with a header row. |
| `revocations_subset.txt` | Auto-revocation list: organizations whose tax-exempt status the IRS revoked, pipe separated, no header row. |

## EO BMF columns (header row in each file)

`EIN, NAME, ICO, STREET, CITY, STATE, ZIP, GROUP, SUBSECTION, AFFILIATION, CLASSIFICATION, RULING, DEDUCTIBILITY, FOUNDATION, ACTIVITY, ORGANIZATION, STATUS, TAX_PERIOD, ASSET_CD, INCOME_CD, FILING_REQ_CD, PF_FILING_REQ_CD, ACCT_PD, ASSET_AMT, INCOME_AMT, REVENUE_AMT, NTEE_CD, SORT_NAME`

- `RULING`: year and month the exemption was ruled, `YYYYMM`.
- `ASSET_AMT`: dollars, as reported on the most recent return.
- `NTEE_CD`: National Taxonomy of Exempt Entities code.

## Revocation list columns (no header row)

`EIN | legal name | doing-business-as name | address | city | state | ZIP | country | exemption type | revocation date | revocation posting date | exemption reinstatement date`

Dates are `DD-MON-YYYY` (for example `15-NOV-2017`). The list holds every revocation the IRS has posted, including ones for organizations that were later reinstated; the last column is the reinstatement date, empty when the organization was not reinstated.
