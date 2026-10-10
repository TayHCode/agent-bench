# Release validation, 2026-10-10

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

The full suite passes 178 tests, including the shipping-tree private path,
email, machine-name and credential-shape checks. Every built-in task has a public
source and full licence notice listed in README and THIRD_PARTY_NOTICES. The
81 historical measured rows retain their numbers; the omitted pilot uses a
generic label with its removal reason in the CSV. No omitted-pilot source or
notice ships.

The fixed release scanner remains unchanged. New credential false positives
were resolved in source: authentication prose, a fake-login placeholder,
parentheses around a public dataset tuple, and a prompt-only lookup variable
rename with identical types/behavior. Exact reviews cover the pinned upstream
mypy regression filename and a synthetic loopback HTTP fixture. Previous exact
public-data and test-fixture reviews are retained privately. No secret, email,
private term or licence finding is approved.

The one-commit export and its audit/digest records are private release artifacts.
No repository publication or visibility change is part of this validation.
