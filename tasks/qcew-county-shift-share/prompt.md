We need the county employment brief updated using the BLS QCEW files in `data/`.
Compare first quarter 2025 with first quarter 2026 for private-sector employment
in the 50 states and DC. The team wants a classic national-growth / industry-mix /
regional-competitiveness shift-share table, and a county rollup that reconciles
back to the published total. Please leave a reproducible script as well as the
CSV deliverables; don't just copy the rounded growth rates or wage averages from
BLS. Use all three monthly employment counts to represent the quarter.

There are multiple overlapping levels in these exports, and the older archive
also contains other quarters. Keep the original BLS county and sector codes,
including combined manufacturing, retail and transportation sectors. Unknown
county records aren't counties. Treat withheld cells as unavailable rather than
zero. An absent sector in either vintage also isn't evidence of zero employment.
Use the union of county-sector keys present in either vintage; the county universe
comes from published private all-industry county rows in either vintage.

For each county-sector pair, put `missing`, `suppressed`, `no_national`, or `ok`
in `status` (in that order of precedence). `no_national` means a missing,
withheld or zero-base national sector benchmark. Keep each vintage's employment
if available, and its difference if both are available. Compute the three
shift-share contributions only for `ok` pairs, with the all-industry national
private growth rate and that sector's national private growth rate. For those
same pairs, add the current employment location quotient and both weekly wages
from wage totals and quarterly mean employment (13 weeks), plus wage growth in
percent. Leave ratios with unavailable or zero denominators blank. Other metrics
on unavailable pairs are blank. Zero employment itself is a valid observation.

The county rollup should sum contributions over the `ok` pairs only and show
how much of the published total change remains unallocated. Use unrounded
values throughout; six decimal places in the final CSVs are enough. IDs stay text.
The column contract is in `README.md`. Please explain any counties with a large
unallocated residual and how you handled non-disclosure.
