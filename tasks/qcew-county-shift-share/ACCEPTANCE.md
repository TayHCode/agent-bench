# QCEW acceptance — 2026-10-10

`agentbench task prepare qcew-county-shift-share` downloaded both original BLS
archives into a fresh prepared task. SHA-256 matched both pins in
`data_recipe.toml`. The visible repo contains only those input ZIPs and the field
contract; reference construction and known answers remain outside it. Exact
answers contain 58,712 county-sector rows and 3,143 county rows. From this fresh
prepare, the start fails and gold passes twice without flakiness. The earlier
independent full-table DuckDB cross-check remains applicable to these same pins.

Exactly one new Sonnet 5.5 / Claude Code probe ran, with verified medium effort,
300,000 fresh tokens, 20 minutes and $1.50 per-run ceilings. Preparation and
hidden checks are outside the agent clock and meter. Model identity was verified,
no peek was detected, and the process completed without a cap or harness error.

- Time: 143.8 seconds (2.40 minutes).
- Full hidden check: FAIL. Both CSVs exist, but both have missing or extra keys.
- Produced rows: 58,458 county-sector rows and 3,126 county rows.
- Cost: $0.20273 dollar-equivalent; CLI-reported $0.1868228.
- Fresh tokens: 28,719.
- New spend: $0.20273, below the $1.60 total allowance. No rerun was purchased.

The previous 81.5-second / $0.12195 missing-deliverable run is excluded from
difficulty evidence. This replacement received and read the checksum-pinned
inputs and produced deliverables at the contracted paths, so missing task data
cannot explain this failure.

Retain QCEW as a hard candidate under the failed-check criterion; n=1 does not
establish a 10–30 minute successful solve. It did not pass in under four minutes,
so the requested medium-label rule does not apply. Checks, required rows,
tolerances and original data were not weakened or hardened. The field contract
now states explicitly that deliverables belong in the repository root.

Raw transcript, checkout and run JSON remain private, outside shipping files.
