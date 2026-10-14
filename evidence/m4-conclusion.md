## Completed M4 cells

The original 13 M4 cells used a 300,000 fresh-token limit: 12 finished and one was capped. The three formerly missing cells are now recorded under a separate 1,000,000 fresh-token profile, bringing the round to 16 recorded cells: 14 finished, two capped, 11 passed, and three failed. The two capped runs both produced work that passed the hidden check. Every cell is n=1, so these outcomes do not establish reliability or rank contestants.

| Task | Contestant | Result | Hidden check | Wall s | Total tokens | Fresh tokens | Dollar-equivalent | Guard | Finished or capped |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| werkzeug-apply-conditions | Astra 6 · Codex | capped | passed | 265 | 639,073 | 56,289 | $1.51591 | $1.49 | capped |
| mypy-deferred-alias-crash | Astra 6 · Codex | pass | passed | 150 | 583,984 | 42,288 | $1.12590 | $1.40 | finished |
| mypy-deferred-alias-crash | Opus + Sonnet team · Claude Code | pass | passed | 222 | 594,377 | 83,419 | $0.82981 | $1.85 | finished |

The three cells cost $3.47162 in recorded dollar-equivalent usage, below the approved $5 ceiling; their estimate from corresponding M3 cells was $2.94. The Astra/Werkzeug run exceeded its nominal $1.49 dollar guard by $0.02591 before the runner stopped it, so the remaining per-cell guards were reduced to $1.40 and $1.85. All three cells also had a 1,000,000 fresh-token limit and a 20-minute limit. Dollar-equivalents use the dated list-price table and are not invoices.

Astra 6 passed the mypy task; the Opus + Sonnet team also passed mypy. Astra's Werkzeug work passed the hidden check but the benchmark scored the run as capped because the dollar meter stopped it. The original 300k M4 cells and the 1,000k completion cells are listed separately in the results so the changed cap is not pooled with historical measurements. The older M2 and M3 rounds remain cap-distorted, with 8 and 13 capped runs respectively; no historical measurements changed.

The results do not rank contestants, show variance, or establish whether teams help on tasks of this size. They also do not show whether Astra's two outcomes generalize beyond these two tasks. The 1,000k M4 completion profile stays separate from the original 300k profile in every table.
