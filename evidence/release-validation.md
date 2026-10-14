# Archived release validation, 2026-10-10

The merged release was installed as a wheel into a fresh Python 3.12 virtual
environment. A README-only rehearsal with an empty HOME passed: `doctor`, the
free `demo`, toy `task from-commit` (start fails and gold passes twice), prompt
editing, a stub-only plan, one `stub-solver` run ($0, pass), and preparation of
`mypy-paramspec-unpack-crash` from its pinned public commits. This verifies the
local Linux workflow; native Windows uses WSL, and real macOS subscription runs
remain unverified.

The public `task prepare` command now also downloads and checksum-verifies QCEW
inputs and constructs its hidden answers outside the visible repository. A fresh
download reproduced 58,712 county-sector rows and 3,143 county rows; start fails
and gold passes twice. The single valid
Sonnet probe failed in 2.40 minutes at $0.20273 equivalent because both
output keysets were incomplete. See the task's acceptance record. Synthetic preparation tests cover actual tiny archive
downloads, checksum rejection, preservation of existing tasks and both check
outcomes without paid model calls.

At that date the full suite passed 178 tests, including shipping-tree checks. This is an archival observation, not the current test count or a complete privacy assurance. Every built-in task has a public
source and full licence notice listed in README and THIRD_PARTY_NOTICES. The
81 historical measured rows retain their numbers; the omitted pilot uses a
generic label with its removal reason in the CSV. No omitted-pilot source or
notice ships.

The fixed release scanner remains unchanged. New credential false positives
were resolved in source: authentication prose, a fake-login placeholder,
parentheses around a public dataset tuple, and a prompt-only lookup variable
rename with identical types/behavior. Exact reviews cover the pinned upstream
mypy regression filename and a synthetic loopback HTTP fixture. Previous exact
public-data and test-fixture reviews are retained privately. The later release audit found that the privacy test itself embedded private terms, contradicting the earlier clean-term claim. The rework removed that table and moved real-term input outside the repository; default tests explicitly announce synthetic mode. Findings are described by category only: local account, internal tools, private project and repository, machine naming, and session folder.

The one-commit export and its audit/digest records are private release artifacts.
No repository publication or visibility change is part of this validation.

The current measurement CSV has 84 rows, including the three completion cells. Current verification counts belong in the private build evidence. Private Git history still contains prior terms and personal metadata: release must use a fresh single-commit export, and history must not be published.

## Check it yourself

From a fresh clone's root, install using the README quickstart, then create an
ignored output folder with `mkdir -p .scratch` (expected exit code 0). This single
offline command checks both v1-r3 and v1-r8 without running any agents:

```sh
agentbench report --results-csv evidence/results.csv --md .scratch/check-results.md --conclusion evidence/m4-conclusion.md
```

Expected exit code: 0. Open `.scratch/check-results.md` and check:

- **v1-r3 — token-limit marking:** In `All runs`, token-limited rows have
  `capped` in both `Result` and `Finished or capped`, with a specific `Cap reason`.
  Examples include `yes: tokens 426296 > 400000` and
  `yes: fresh tokens 302087 > 300000`.
- **v1-r8 — limited rerun cost:** `All runs` contains exactly three rows with
  the `m4: 1000k fresh tokens` profile. `Completed M4 cells` identifies those
  three added cells and records their total as $3.47162, below the approved $5
  ceiling. The CSV's rounded costs sum to $3.4716; the conclusion retains finer
  precision. The other 81 rows use the older profiles.

## Update export privacy review, 2026-10-14

The release review targets an update to the existing public repository. Its
current source tree has no personal, credential or media findings in the
word-boundary scanner; private history still has findings and must stay private.
Use a flattened single-commit snapshot, preserving the current licences and
source attribution. Fresh README verification and suite results are recorded
with that exact snapshot in private evidence, rather than inferred from the
archival counts above.

The scanner's export-from-history check also reports old versions of
THIRD_PARTY_NOTICES.md and licences for a removed pilot whose source no longer
ships. It checks every historical notice line against the current notice and
requires removed licence paths, without checking which source the snapshot
contains. Those findings require scanner review; they are distinct from
scanning the snapshot itself. Do not restore omitted source, erase current
attribution or suppress privacy checks to make that history check pass.
