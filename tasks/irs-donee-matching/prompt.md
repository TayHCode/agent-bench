Our giving committee keeps a list of the organizations we have given to over the years (`donees.csv`:
name, city, state, taken from IRS Publication 78 and with no EINs). For the quarterly review I need each one
matched to its record in the IRS data in this folder (see `README.md`), together with its revocation status.

Write `matched.csv` (UTF-8, comma-separated, header row, same rows in the same order as `donees.csv`) with these
columns in this order:

1. `name`, 2. `city`, 3. `state`: copied unchanged from `donees.csv`
4. `ein`: the organization's EIN as `NN-NNNNNNN`
5. `match`: `one` when exactly one organization in the BMF extracts is that organization, `many` when more than one is
   (then leave `ein` and everything after it blank, do not guess), `none` when none is (also leave the rest blank)
6. `ntee`: the BMF `NTEE_CD`
7. `ruling`: the BMF `RULING` as `YYYY-MM`
8. `assets_usd`: the BMF `ASSET_AMT` as a whole number of dollars, blank if there is none
9. `revoked`: `Y` if the IRS has revoked the organization's exemption and has not reinstated it, otherwise `N`
10. `revoked_on`: the date of that revocation as `YYYY-MM-DD`, blank unless `revoked` is `Y`

Two records are the same organization when their name, city and state agree once the differences in how the two
files write them are ignored. Do not match organizations that merely look similar.

When you are done, tell me how many rows have each `match` value and how many organizations are `revoked` = `Y`.
