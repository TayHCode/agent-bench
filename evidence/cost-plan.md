# agent-bench cost plan (M0, 2026-10-09)

Design aim: keep initial experiments quick and cheap. The earlier plan was smoke about $26 and pilot about $80 for 14 and 42 runs. This plan replaces it. All dollar figures are **estimates** from a micro-task profile (15k cache-write, 60k cache-read, 6k output tokens per solo run), priced from the versioned public table (`prices.toml`, 2026-10-09). The one real micro-run so far (Haiku 5.5, 44k tokens) cost $0.0038, matching the vendor figure. Opus, Astra and team numbers are not yet measured.

## What changes

1. **Micro-tasks only.** A task enters the pool only if a solo run finishes in under 10 minutes and under 100k tokens (Haiku sets the bar: it is the cheapest to test). Drop the 25-60 minute breadth tasks until later.
2. **4 tasks x 1 repeat first.** Repeats only where intervals overlap (top four contestants, 2 extra repeats). Before: 6 tasks, repeats everywhere.
3. **One effort level for all: `medium`** (Claude Code `--effort medium`, Codex `-c model_reasoning_effort=medium`). Both CLIs accept it (measured in the preliminary CLI probes). The spec said `high`; medium cuts output and reasoning tokens, the priciest part.
4. **Hard caps per run in tokens, dollars and minutes, enforced by the runner from the live stream** (kill, record `capped`). M0 showed vendor budget flags are not enough: `--max-budget-usd 0.15` did not stop an Opus run that cost $2.08.
5. **Cheap first, gate the expensive.** Run Haiku and Sonnet on all 4 tasks. Run Sol next. Run Astra, Opus and both teams only on tasks where a cheap contestant produced a valid, checkable result (hidden test runs, fails on the unfixed repo, passes on the gold fix). These runs are pilot data, not extra.
6. **Strip fixed overhead:** `--strict-mcp-config` (removes 78 account-connector tool schemas), `--setting-sources ""`, an explicit six-tool list, clean HOME. Keep the prefix identical across repeats so prompt caching hits (Codex cached 12,288 of 14,361 prompt tokens in M0; Claude Code caches automatically).
7. **Existing subscriptions:** Claude contestants run in Claude Code on the study's Claude login, OpenAI contestants in Codex on the study's Codex login. Tokens still come from transcripts and the dollar-equivalent from the public price table. This uses subscription usage, which has its own limits; the report labels every figure "dollar-equivalent, subscription run". Nothing to approve.
8. **Reuse:** Opus solo is the shared baseline for both team comparisons; sub-agent-free solo runs are never repeated per group. A task whose Haiku and Sonnet runs both pass or both fail identically at medium can skip repeats.
9. **Judge:** a Gemini model, secondary only, run only on passing outputs. Gemini pricing not verified; budgeted at about $0.01 per run.

## Estimated $ per run and per step

| Run type | Est. $/run | Hard cap $/run (about 3x) | Tokens cap | Minutes cap |
|---|---|---|---|---|
| Haiku 5.5 + Claude Code | 0.007 | 0.03 | 150k | 10 |
| Sol 6.1 + Codex | 0.10 | 0.30 | 150k | 10 |
| Sonnet 5.5 + Claude Code | 0.13 | 0.40 | 150k | 10 |
| Opus 5.5 + Claude Code | 0.25 | 0.75 | 150k | 10 |
| Astra 6 + Codex | 0.51 | 1.50 | 150k | 10 |
| Team A: Opus + 3-5 Sonnet | 0.43 | 1.30 | 400k | 15 |
| Team B: Opus + 10-20 Haiku | 0.22 | 0.70 | 400k | 15 |
| **All 7 types, one task** | **1.64** | | | |

| Step | Est. $ |
|---|---|
| 1. Gate: Haiku + Sonnet, 4 tasks | 0.53 |
| 2. Sol, 4 tasks | 0.38 |
| 3. Opus solo, 4 tasks | 1.00 |
| 4. Astra, validated tasks | 2.04 |
| 5. Team A, validated tasks | 1.72 |
| 6. Team B, validated tasks | 0.88 |
| 7. Two extra repeats of the top four where close (4 tasks) | 11.28 |
| 8. Gemini judge | 0.50 |
| 9. 20% reruns and failures | 3.67 |
| **Pilot total (smoke included)** | **about 22** |

## Recommended budgets

- **Smoke: 2 tasks x 7 types x 1 = 14 runs, about $3.3; budget $4, hard cap $5** (a run ledger stops the run when the cap is reached, whatever the per-run caps allow). Down from about $26.
- **Pilot: 4 tasks, steps 1-9, about $22; hard cap $25, smoke runs counted inside it.** Down from about $80.
- **M0 itself:** capped at $5 dollar-equivalent; preliminary personal notes and raw records are omitted from this export.
- The full run (20 tasks) needs a new owner decision after real token counts.
