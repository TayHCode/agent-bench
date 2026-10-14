# M2: pilot run on the other three tasks, and the results page (2026-10-10)

Results: `evidence/m2-pilot-results.html` (one self-contained page) and `evidence/m2-pilot-results.md` (same tables). Both were originally produced by
`agentbench report --html evidence/m2-pilot-results.html --md evidence/m2-pilot-results.md --conclusion evidence/m2-conclusion.md`.
Unshipped raw run records stayed under `runs/` (ignored by git); `agentbench backfill` adds the per-file diff and worker count to older records.

## What ran

Seven contestants x three tasks (humanize-intcomma-overflow, taskiq-lazy-logging, removed-pilot-task), one process at a time, medium effort, connectors off, clean HOME, per-run token/dollar/minute caps enforced. removed pilot's token cap was raised to 250k (task.toml `max_tokens`); everything else used the cost-plan caps. Order: Haiku, Sonnet, Sol, Opus, then Astra and the two teams once a cheap contestant had produced a checkable result (it had on every task). Then a second repeat of every cell: capped cells first, then the rest cheap-first, until all 21 cells had two runs. The fda smoke task stays at n=1. The earlier Haiku probes on humanize and taskiq count as repeat 1 for those cells.

## Spend (dollar-equivalent, subscription runs)

| Item | $ |
|---|---|
| This step, 40 new recorded runs (the 2 earlier humanize/taskiq Haiku probes and the superseded removed pilot probe are in the smoke row) | 9.50 |
| This step, 3 runs lost to the missing-stub fault (not in any table) | 0.31 |
| **This step total (hard cap 14)** | **9.81** |
| Smoke (7 runs) plus the three earlier Haiku probes | 1.57 |
| **Pilot ledger to date (cap 25)** | **11.38** |

## What broke

1. **Missing `_version.py` in the humanize start checkout.** The upstream `.gitignore` hides it, so the stub existed only in the old worktree, never in git. In the new worktree the first Sonnet and Sol runs and a started Opus run could not import `humanize`, and the hidden check failed on import for reasons unrelated to their work. Stopped after two records and one killed run (about $0.31), tracked the file (`git add -f`), added a test that it is tracked, re-ran `verify`, and re-ran all three. Those records are kept out of the results (`runs/_invalid`).
2. **Haiku/removed pilot probe under the old 150k cap** is kept out (`runs/_superseded`): same configuration except the cap, which the task now raises.
3. **The 150k token cap decides the taskiq outcome.** Tokens include cached input. Every miss in the pilot is a cap kill on taskiq; five of the eight kills had already left work that passed the hidden check. Not changed after the fact; flagged in the report and conclusion.
4. Capped team runs had no `subagent_stats`, so their worker count was blank; the runner now counts sub-agent session files, and `backfill` fixed the existing records (swarm cap kills show 10 workers).
5. gold comparison needed two rules: lockfiles an install writes (removed pilot `package-lock.json`, 1,221 lines) are not counted, and three type-annotation files the taskiq PR reordered for unrelated reasons are listed in that manifest's `[gold_comparison] ignore`.

## Failures, one line each

All eight are cap kills on taskiq-lazy-logging; no run finished and then failed the check.

- Sol 6.1 (twice): killed at 152k tokens, 11 files edited, hidden check passed on what it had written.
- Astra 6 (twice): killed at 161k and 153k tokens, 11 files edited, hidden check passed.
- Opus 5.5: killed at 166k tokens (its other run passed at 149k), 11 files edited, hidden check passed.
- Haiku 5.5: killed at 156k tokens (its other run passed at 118k), 7 of 11 files edited, ruff still reported 7 findings.
- Opus + Haiku swarm (twice): killed at 410k and 412k tokens with 10 workers; one run had not added `"G"` to the ruff select list, the other left 1 ruff finding.

## Passing diffs against the real fix (changed source lines, tests and lockfiles excluded)

- removed pilot (real fix 2 lines): Sol, Astra, Sonnet 2 lines; Haiku 2-3; Opus 4-6; Opus + Sonnet team 4-7; swarm 2 and 11. All touched the one file the fix touched.
- humanize (real fix 2 lines): Sol 2, Astra 3, Haiku 3-8; Sonnet 21-24; Opus 26-61; teams 8-25. All touched the one file the fix touched.
- taskiq (real fix 85 lines excluding the 3 unrelated files): all passing runs 63-70 lines in the same 11 files.

These archived reports received presentation repairs after generation. Their raw historical sessions are not shipped, so full regeneration is unavailable; the rounded per-run measurements remain in `results.csv`.
