# M3: three harder tasks and the seven-contestant run (2026-10-10)

Results: `evidence/m3-results.html` and `evidence/m3-results.md` (pilot plus the new tasks, seven tasks), conclusion in `evidence/m3-conclusion.md`. Originally produced by
`agentbench report --runs runs-m2 runs --html evidence/m3-results.html --md evidence/m3-results.md --conclusion evidence/m3-conclusion.md --title "agent-bench results: pilot plus three harder tasks"`.
Unshipped raw run records stayed under `runs/` (new), `runs-m2/` (copies of the pilot's) and `runs-probes/` (difficulty probes of dropped or superseded tasks); all ignored by git.

## The three tasks (each proven: the unfixed start fails the check, the real fix passes it; `agentbench verify --task <id>`)

| Task | Kind | Source (licence) | Real fix | Hidden check | verify |
|---|---|---|---|---|---|
| werkzeug-apply-conditions | multi-file feature/fix from an issue text | pallets/werkzeug PR 3308, issue 3291 (BSD-3-Clause); merged 2026-09-27 | 864 changed source lines in 8 files (plus docs and tests) | upstream tests for `Response.apply_conditions` and `apply_range` plus the wrappers and http suites, 247 tests; warnings are errors | start 45 failed / 202 passed, fix 247 passed |
| mypy-deferred-alias-crash | debugging from a real crash log | python/mypy PR 22096, issue 21933 (MIT); merged 2026-10-05 | 12 changed lines in `mypy/semanal.py` (plus 2 test cases) | the 2 new upstream test-data cases and 7 type-check suites, 1,150 selected tests; any fix that removes the crash and gives the right types passes | start 2 failed / 1,147 passed, fix 1,149 passed |
| irs-donee-matching | messy data, two public sources plus an events table | IRS EO BMF (5 state extracts), Publication 78, auto-revocation list (public domain, US government work); fetched 2026-10-10 | n/a | 709-row known answer cell for cell, at most 3 wrong rows | start: no output file; fix: 0 wrong |

Each prepared folder has `prompt.md`, `repo/` (a fresh single-commit checkout when run), `hidden/` (copied in only after the run), `gold/` (the real fix, or the known answer), `LICENSE-SOURCE`, and `manifest.toml` (source URL, base and fix commits, dates, licence, author check, why it matches a real workflow, and the five-question workflow-match check answered). In this export the code tasks ship pinned recipes: `agentbench task prepare TASK_ID` downloads and reconstructs their source, regression tests and gold. Data inputs and answers ship directly. The workflow questions document relevance and are not a gate decided by a model.

- **werkzeug-apply-conditions**: the prompt is the maintainer's design issue (a list of RFC 9110 defects in `make_conditional`) plus his follow-up comment, and a short interface section (method names, the `exists` keyword, the exceptions, and that `apply_range` works from `Content-Length`) taken from the PR because the hidden tests call those names. The first version of the prompt left out the `Content-Length` rule; a probe failed one hidden test on it, so the line was added and the probes were run again (the first probes are in `runs-probes/superseded-task-versions`).
- **mypy-deferred-alias-crash**: the prompt is the user's crash report with the full traceback and reproducer, plus a commenter's variant. The traceback ends in `tuple_fallback`; the cause is earlier, in semantic analysis, where a deferred type alias gets a new node instead of an in-place update. mypy's own CI had no failing run for this, so the user's crash log is the real log. A symptom patch (in `typeops.py`) makes the crash go away but reveals the wrong type, so the regression cases catch it.
- **irs-donee-matching**: 709 name/city/state rows from Publication 78 with the EINs withheld (the true EIN is the answer); the agent matches them to the BMF extracts (the BMF writes some names with a lost space where it wrapped them over two fields; case, punctuation and abbreviations differ), enriches them (dates `YYYYMM`, dollars), and derives a revocation status from the headerless pipe file with `DD-MON-YYYY` dates, several rows per EIN and reinstatements. The reference was first wrong about organizations that Pub 78 lists but the BMF extracts do not (a same-name organization with another EIN exists in the extracts); the probes exposed it, the build script was fixed and the probes rerun.

## How the tasks were chosen

Screened with `gh` over about 150 public repositories (Python and TypeScript; no Go toolchain was installed and none was downloaded), merged PRs after 2026-06-30 only, permissive licences only, human authors only.

- Dropped because the PR text says an AI wrote it: xarray PR 11608 (Claude Code with Opus 5.5), fastmcp PRs 5374 and 5558 ("Generated with Pi"). mypy and scrapy carry Claude/Codex trailers on other commits and none on the kept PRs; werkzeug's has none. An undisclosed AI-written fix cannot be detected this way.
- Dropped for the environment: Poetry's solver KeyError (needs an unreleased poetry-core), Flask's dev-versions CI failure (needs unreleased Werkzeug from git), the pydantic PRs (Rust core built from source).
- Failing CI runs on public main branches were searched (about 100 repositories); the ones found were macOS/Windows-only, flaky, or fixed by changing the test, so the debugging task uses a user's crash log instead.

## Difficulty probes (one run each, Haiku 5.5 and Sonnet 5.5, 400k-token cap)

Rule applied: if both probes passed (or left passing work) in under about two minutes, replace the task. 18 probe runs:

| Task | Contestant | Result | Work passes check | Wall s | Tokens | $ equiv | Group |
|---|---|---|---|---|---|---|---|
| irs-charity-recipients | haiku-5-5 | pass | yes | 40 | 133,447 | $0.009 | rejected-too-easy |
| irs-charity-recipients | sonnet-5-5 | pass | yes | 15 | 41,640 | $0.052 | rejected-too-easy |
| mypy-overload-union-subtype | haiku-5-5 | pass | yes | 125 | 318,665 | $0.012 | rejected-too-easy |
| mypy-overload-union-subtype | sonnet-5-5 | pass | yes | 47 | 87,192 | $0.098 | rejected-too-easy |
| scrapy-priority-queues | haiku-5-5 | capped | yes | 82 | 402,330 | $0.020 | rejected-too-easy |
| scrapy-priority-queues | sonnet-5-5 | pass | yes | 77 | 191,944 | $0.182 | rejected-too-easy |
| sec-annual-revenue | haiku-5-5 | pass | yes | 55 | 369,522 | $0.018 | rejected-too-easy |
| sec-annual-revenue | sonnet-5-5 | pass | yes | 20 | 42,001 | $0.060 | rejected-too-easy |
| irs-donee-matching | haiku-5-5 | fail | no | 70 | 217,365 | $0.015 | superseded-task-versions |
| irs-donee-matching | sonnet-5-5 | fail | no | 37 | 155,180 | $0.151 | superseded-task-versions |
| werkzeug-apply-conditions | haiku-5-5 | capped | no | 104 | 423,251 | $0.026 | superseded-task-versions |
| werkzeug-apply-conditions | sonnet-5-5 | fail | no | 62 | 189,492 | $0.247 | superseded-task-versions |
| irs-donee-matching | haiku-5-5 | capped | yes | 97 | 426,296 | $0.024 | kept task (counts as the cell run) |
| irs-donee-matching | sonnet-5-5 | pass | yes | 45 | 193,074 | $0.187 | kept task (counts as the cell run) |
| mypy-deferred-alias-crash | haiku-5-5 | capped | no | 94 | 401,085 | $0.017 | kept task (counts as the cell run) |
| mypy-deferred-alias-crash | sonnet-5-5 | fail | no | 51 | 148,854 | $0.122 | kept task (counts as the cell run) |
| werkzeug-apply-conditions | haiku-5-5 | capped | no | 98 | 435,107 | $0.026 | kept task (counts as the cell run) |
| werkzeug-apply-conditions | sonnet-5-5 | capped | yes | 120 | 433,272 | $0.426 | kept task (counts as the cell run) |

- **Replaced as too easy**: scrapy-priority-queues (scrapy PR 8237, BSD-3-Clause), irs-charity-recipients (a precisely specified three-file merge), mypy-overload-union-subtype (mypy PR 22007; Haiku took 125 s), sec-annual-revenue (SEC financial-statement data, several latent traps). Their folders are archived outside the repository (an unshipped archive); their probe runs stay in `runs-probes/rejected-too-easy`.
- **Kept**: mypy-deferred-alias-crash and werkzeug-apply-conditions (neither probe passed inside the caps).
- **Kept with a caveat**: irs-donee-matching, the data task. Sonnet passed in 45 s and Haiku's work passed before the cap cut it at 97 s, so by the rule it is also too easy. It is the hardest of the four data tasks tried and a third replacement was not attempted; the report says so.

## Caps and spend (dollar-equivalent, subscription runs)

Caps per run for the final runs (profile `m3`): tokens 400,000 and minutes 20 for every contestant; dollars Haiku 0.10, Sol 0.60, Sonnet 0.80, Opus 1.50, Astra 2.00, Opus + Sonnet team 2.00, Opus + Haiku swarm 1.50 (each also cut to what was left in the ledger). Effort `medium`, connectors off, clean HOME, one process at a time, as in the pilot.

| Item | $ |
|---|---|
| 19 final runs on the three kept tasks (includes the Haiku and Sonnet probe runs on them, which count as those cells) | 8.40 |
| 12 other probe runs (dropped and superseded task versions) | 0.89 |
| **Step total (hard cap 10)** | **9.30** |
| Pilot ledger before this step | 11.38 |

Order: probes, then Sol, Opus, Astra, the Opus + Sonnet team, the Opus + Haiku swarm. The runner stopped at 90% of the ledger, so the team and the swarm were not run on the data task (2 of 21 cells empty).

## What broke or was wrong

1. **The token cap decided most outcomes again.** 13 of the 19 final runs were killed at 400,000 total tokens, mostly cache reads (fresh tokens were 18,000 to 98,000 in every run on the two code tasks); none hit the dollar cap (highest run $1.32 against $2.00) or the 20-minute cap (longest 7 minutes). The report adds a "work passes the check" column for this reason.
2. **A reference-answer bug** in the data task (above) and **a missing line in the werkzeug prompt** (above) were found only because the probes failed in odd ways; the superseded probe runs are kept and counted in the spend.
3. **An upstream `.gitignore` hid a folder** (`venv/` in mypy's typeshed stubs) from `git add`; a fresh worktree would have lacked it. Force-added, and a test now fails if any file under `tasks/` is ignored.
4. A probe batch was queued with a loop that could not be paused, so it was stopped between runs and replaced by a small queue runner (`.scratch`, not committed); no run was lost.
5. Selection effect: tasks were kept or replaced using Haiku and Sonnet probes, so those two are disadvantaged on the kept tasks by construction.
6. Not done: the optional code-review/audit task (d).

These archived reports received presentation repairs after generation. Their raw historical sessions are not shipped, so full regeneration is unavailable; the rounded per-run measurements remain in `results.csv`.
