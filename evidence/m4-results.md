# M4 results (including historical rounds)

Generated from evidence/results.csv, preserving its recorded rounded measurements. The Finished or capped column records the outcome; cap reasons appear separately in Cap reason. M2 and M3 are cap-distorted historical rounds. Raw historical sessions are not shipped; hidden-check outcomes on capped work and per-file diff comparisons cannot be reconstructed from this table. The three completion cells' check outcomes and finer cost precision are recorded in evidence/m4-conclusion.md. Dollar-equivalents are not invoices. Each M4 cell is n=1.

## Conclusion

### Completed M4 cells

The original 13 M4 cells used a 300,000 fresh-token limit: 12 finished and one was capped. The three formerly missing cells are now recorded under a separate 1,000,000 fresh-token profile, bringing the round to 16 recorded cells: 14 finished, two capped, 11 passed, and three failed. The two capped runs both produced work that passed the hidden check. Every cell is n=1, so these outcomes do not establish reliability or rank contestants.

| Task | Contestant | Result | Hidden check | Wall s | Total tokens | Fresh tokens | Dollar-equivalent | Guard | Finished or capped |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| werkzeug-apply-conditions | Astra 6 · Codex | capped | passed | 265 | 639,073 | 56,289 | $1.51591 | $1.49 | capped |
| mypy-deferred-alias-crash | Astra 6 · Codex | pass | passed | 150 | 583,984 | 42,288 | $1.12590 | $1.40 | finished |
| mypy-deferred-alias-crash | Opus + Sonnet team · Claude Code | pass | passed | 222 | 594,377 | 83,419 | $0.82981 | $1.85 | finished |

The three cells cost $3.47162 in recorded dollar-equivalent usage, below the approved $5 ceiling; their estimate from corresponding M3 cells was $2.94. The Astra/Werkzeug run exceeded its nominal $1.49 dollar guard by $0.02591 before the runner stopped it, so the remaining per-cell guards were reduced to $1.40 and $1.85. All three cells also had a 1,000,000 fresh-token limit and a 20-minute limit. Dollar-equivalents use the dated list-price table and are not invoices.

Astra 6 passed the mypy task; the Opus + Sonnet team also passed mypy. Astra's Werkzeug work passed the hidden check but the benchmark scored the run as capped because the dollar meter stopped it. The original 300k M4 cells and the 1,000k completion cells are listed separately in the results so the changed cap is not pooled with historical measurements. The older M2 and M3 rounds remain cap-distorted, with 8 and 13 capped runs respectively; no historical measurements changed.

The results do not rank contestants, show variance, or establish whether teams help on tasks of this size. They also do not show whether Astra's two outcomes generalize beyond these two tasks. The 1,000k M4 completion profile stays separate from the original 300k profile in every table.

## Recorded rounds

| Round | Runs | Passed | Finished or capped |
|---|---|---|---|
| m2 | 49 | 41 | 41 finished / 8 capped |
| m3 | 19 | 5 | 6 finished / 13 capped |
| m4 | 16 | 11 | 14 finished / 2 capped |

## M3 against M4 (separate cap profiles)

| Task | Contestant | Cap profile | Result | Wall s | Total tokens | Fresh tokens | $ equiv | Workers | Effort (seen) | Cap reason | Finished or capped |
|---|---|---|---|---|---|---|---|---|---|---|---|
| irs-donee-matching | haiku-5-5@claude-code | m3: 400k total tokens, 20 min, $0.1 | capped | 97 | 426296 | 72824 | 0.0238 |  | medium (medium) | yes: tokens 426296 > 400000 | capped |
| irs-donee-matching | sol-6.1@codex | m3: 400k total tokens, 20 min, $0.6 | pass | 91 | 180173 | 17613 | 0.0783 |  | medium (medium) | no | finished |
| irs-donee-matching | sonnet-5-5@claude-code | m3: 400k total tokens, 20 min, $0.8 | pass | 45 | 193074 | 31256 | 0.1870 |  | medium (medium) | no | finished |
| irs-donee-matching | astra-6@codex | m3: 400k total tokens, 20 min, $1.2145 | pass | 84 | 184946 | 23282 | 0.5094 |  | medium (medium) | no | finished |
| irs-donee-matching | opus-5-5@claude-code | m3: 400k total tokens, 20 min, $1.5 | pass | 134 | 196142 | 50878 | 0.5190 |  | medium (medium) | no | finished |
| irs-donee-matching | opus+sonnet-team@claude-code | m4: 300k fresh tokens, 20 min, $2.4299 | pass | 157 | 471676 | 99842 | 0.7915 | 3 | medium (medium) | no | finished |
| irs-donee-matching | opus+haiku-swarm@claude-code | m4: 300k fresh tokens, 20 min, $3 | pass | 167 | 1146606 | 218785 | 0.9228 | 10 | medium (medium) | no | finished |
| mypy-deferred-alias-crash | haiku-5-5@claude-code | m3: 400k total tokens, 20 min, $0.1 | capped | 94 | 401085 | 45138 | 0.0175 |  | medium (medium) | yes: tokens 401085 > 400000 | capped |
| mypy-deferred-alias-crash | haiku-5-5@claude-code | m4: 300k fresh tokens, 20 min, $0.3 | fail | 209 | 598868 | 59000 | 0.0237 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | sol-6.1@codex | m3: 400k total tokens, 20 min, $0.6 | capped | 96 | 431207 | 35431 | 0.1356 |  | medium (medium) | yes: tokens 431207 > 400000 | capped |
| mypy-deferred-alias-crash | sonnet-5-5@claude-code | m3: 400k total tokens, 20 min, $0.8 | fail | 51 | 148854 | 18167 | 0.1223 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | sol-6.1@codex | m4: 300k fresh tokens, 20 min, $1.2 | pass | 127 | 540237 | 39245 | 0.1596 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | opus-5-5@claude-code | m3: 400k total tokens, 20 min, $1.5 | pass | 174 | 256185 | 35651 | 0.4123 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | opus+haiku-swarm@claude-code | m3: 400k total tokens, 20 min, $1.5 | capped | 158 | 434166 | 94393 | 0.6219 | 13 | medium (medium) | yes: tokens 434166 > 400000 | capped |
| mypy-deferred-alias-crash | sonnet-5-5@claude-code | m4: 300k fresh tokens, 20 min, $1.5 | fail | 43 | 131266 | 17605 | 0.1160 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | astra-6@codex | m3: 400k total tokens, 20 min, $2 | capped | 112 | 438214 | 38470 | 0.9088 |  | medium (medium) | yes: tokens 438214 > 400000 | capped |
| mypy-deferred-alias-crash | opus+sonnet-team@claude-code | m3: 400k total tokens, 20 min, $2 | capped | 136 | 413449 | 76586 | 0.7135 | 3 | medium (medium) | yes: tokens 413449 > 400000 | capped |
| mypy-deferred-alias-crash | opus-5-5@claude-code | m4: 300k fresh tokens, 20 min, $3 | pass | 265 | 626464 | 53215 | 0.6694 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | opus+haiku-swarm@claude-code | m4: 300k fresh tokens, 20 min, $3 | pass | 250 | 593287 | 92082 | 0.7139 | 10 | medium (medium) | no | finished |
| werkzeug-apply-conditions | haiku-5-5@claude-code | m3: 400k total tokens, 20 min, $0.1 | capped | 98 | 435107 | 78175 | 0.0261 |  | medium (medium) | yes: tokens 435107 > 400000 | capped |
| werkzeug-apply-conditions | haiku-5-5@claude-code | m4: 300k fresh tokens, 20 min, $0.3 | fail | 268 | 2131566 | 149430 | 0.0664 |  | medium (medium) | no | finished |
| werkzeug-apply-conditions | sol-6.1@codex | m3: 400k total tokens, 20 min, $0.6 | capped | 413 | 441246 | 60702 | 0.2447 |  | medium (medium) | yes: tokens 441246 > 400000 | capped |
| werkzeug-apply-conditions | sonnet-5-5@claude-code | m3: 400k total tokens, 20 min, $0.8 | capped | 120 | 433272 | 63030 | 0.4263 |  | medium (medium) | yes: tokens 433272 > 400000 | capped |
| werkzeug-apply-conditions | sol-6.1@codex | m4: 300k fresh tokens, 20 min, $1.2 | pass | 302 | 1247098 | 84346 | 0.3913 |  | medium (medium) | no | finished |
| werkzeug-apply-conditions | opus-5-5@claude-code | m3: 400k total tokens, 20 min, $1.5 | capped | 185 | 405391 | 77582 | 0.9397 |  | medium (medium) | yes: tokens 405391 > 400000 | capped |
| werkzeug-apply-conditions | opus+haiku-swarm@claude-code | m3: 400k total tokens, 20 min, $1.5 | capped | 128 | 401913 | 91394 | 0.3492 | 6 | medium (medium) | yes: tokens 401327 > 400000 | capped |
| werkzeug-apply-conditions | sonnet-5-5@claude-code | m4: 300k fresh tokens, 20 min, $1.5 | pass | 61 | 171454 | 35434 | 0.2213 |  | medium (medium) | no | finished |
| werkzeug-apply-conditions | opus+sonnet-team@claude-code | m4: 300k fresh tokens, 20 min, $1.6385 | pass | 237 | 998512 | 155377 | 1.2842 | 4 | medium (medium) | no | finished |
| werkzeug-apply-conditions | astra-6@codex | m3: 400k total tokens, 20 min, $2 | capped | 215 | 452646 | 56614 | 1.3230 |  | medium (medium) | yes: tokens 452646 > 400000 | capped |
| werkzeug-apply-conditions | opus+sonnet-team@claude-code | m3: 400k total tokens, 20 min, $2 | capped | 179 | 406471 | 97543 | 0.8464 | 4 | medium (medium) | yes: tokens 406394 > 400000 | capped |
| werkzeug-apply-conditions | opus-5-5@claude-code | m4: 300k fresh tokens, 20 min, $3 | pass | 278 | 705875 | 102425 | 1.2756 |  | medium (medium) | no | finished |
| werkzeug-apply-conditions | opus+haiku-swarm@claude-code | m4: 300k fresh tokens, 20 min, $3 | capped | 209 | 1400130 | 302140 | 0.9999 | 11 | medium (medium) | yes: fresh tokens 302087 > 300000 | capped |
| werkzeug-apply-conditions | astra-6@codex | m4: 1000k fresh tokens, 20 min, $1.49 | capped | 265 | 639073 | 56289 | 1.5159 |  | medium (medium) | yes: usd 1.5159 > 1.49 | capped |
| mypy-deferred-alias-crash | astra-6@codex | m4: 1000k fresh tokens, 20 min, $1.4 | pass | 150 | 583984 | 42288 | 1.1259 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | opus+sonnet-team@claude-code | m4: 1000k fresh tokens, 20 min, $1.85 | pass | 222 | 594377 | 83419 | 0.8298 | 3 | medium (medium) | no | finished |

## fda-recalls-clean

| Task | Contestant | Cap profile | Result | Wall s | Total tokens | Fresh tokens | $ equiv | Workers | Effort (seen) | Cap reason | Finished or capped |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fda-recalls-clean | haiku-5-5@claude-code | m2: 150k total tokens, 10 min, $0.03 | pass | 18 | 52896 | 15616 | 0.0047 |  | medium (medium) | no | finished |
| fda-recalls-clean | sol-6.1@codex | m2: 150k total tokens, 10 min, $0.3 | pass | 25 | 85836 | 12492 | 0.0419 |  | medium (medium) | no | finished |
| fda-recalls-clean | sonnet-5-5@claude-code | m2: 150k total tokens, 10 min, $0.4 | pass | 13 | 39830 | 7995 | 0.0469 |  | medium (medium) | no | finished |
| fda-recalls-clean | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | pass | 123 | 338705 | 111465 | 0.5681 | 10 | medium (medium) | no | finished |
| fda-recalls-clean | opus-5-5@claude-code | m2: 150k total tokens, 10 min, $0.75 | pass | 31 | 54313 | 16630 | 0.1786 |  | medium (medium) | no | finished |
| fda-recalls-clean | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 63 | 187778 | 49077 | 0.4205 | 3 | medium (medium) | no | finished |
| fda-recalls-clean | astra-6@codex | m2: 150k total tokens, 10 min, $1.5 | pass | 30 | 85253 | 18053 | 0.2917 |  | medium (medium) | no | finished |

## humanize-intcomma-overflow

| Task | Contestant | Cap profile | Result | Wall s | Total tokens | Fresh tokens | $ equiv | Workers | Effort (seen) | Cap reason | Finished or capped |
|---|---|---|---|---|---|---|---|---|---|---|---|
| humanize-intcomma-overflow | haiku-5-5@claude-code | m2: 150k total tokens, 10 min, $0.03 | pass | 17 | 66170 | 15720 | 0.0047 |  | medium (medium) | no | finished |
| humanize-intcomma-overflow | haiku-5-5@claude-code | m2: 150k total tokens, 10 min, $0.03 | pass | 25 | 118077 | 17188 | 0.0058 |  | medium (medium) | no | finished |
| humanize-intcomma-overflow | sol-6.1@codex | m2: 150k total tokens, 10 min, $0.3 | pass | 32 | 113722 | 15546 | 0.0467 |  | medium (medium) | no | finished |
| humanize-intcomma-overflow | sol-6.1@codex | m2: 150k total tokens, 10 min, $0.3 | pass | 23 | 102855 | 14663 | 0.0442 |  | medium (medium) | no | finished |
| humanize-intcomma-overflow | sonnet-5-5@claude-code | m2: 150k total tokens, 10 min, $0.4 | pass | 21 | 51401 | 9880 | 0.0614 |  | medium (medium) | no | finished |
| humanize-intcomma-overflow | sonnet-5-5@claude-code | m2: 150k total tokens, 10 min, $0.4 | pass | 21 | 51250 | 11038 | 0.0666 |  | medium (medium) | no | finished |
| humanize-intcomma-overflow | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | pass | 68 | 296521 | 72678 | 0.3383 | 10 | medium (medium) | no | finished |
| humanize-intcomma-overflow | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | pass | 132 | 338379 | 89552 | 0.4876 | 10 | medium (medium) | no | finished |
| humanize-intcomma-overflow | opus-5-5@claude-code | m2: 150k total tokens, 10 min, $0.75 | pass | 81 | 123233 | 29472 | 0.3452 |  | medium (medium) | no | finished |
| humanize-intcomma-overflow | opus-5-5@claude-code | m2: 150k total tokens, 10 min, $0.75 | pass | 58 | 54442 | 17946 | 0.2146 |  | medium (medium) | no | finished |
| humanize-intcomma-overflow | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 48 | 191280 | 42542 | 0.3234 | 3 | medium (medium) | no | finished |
| humanize-intcomma-overflow | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 87 | 179881 | 63350 | 0.4436 | 3 | medium (medium) | no | finished |
| humanize-intcomma-overflow | astra-6@codex | m2: 150k total tokens, 10 min, $1.5 | pass | 28 | 124730 | 25786 | 0.3953 |  | medium (medium) | no | finished |
| humanize-intcomma-overflow | astra-6@codex | m2: 150k total tokens, 10 min, $1.5 | pass | 21 | 110565 | 22757 | 0.3406 |  | medium (medium) | no | finished |

## irs-donee-matching

| Task | Contestant | Cap profile | Result | Wall s | Total tokens | Fresh tokens | $ equiv | Workers | Effort (seen) | Cap reason | Finished or capped |
|---|---|---|---|---|---|---|---|---|---|---|---|
| irs-donee-matching | haiku-5-5@claude-code | m3: 400k total tokens, 20 min, $0.1 | capped | 97 | 426296 | 72824 | 0.0238 |  | medium (medium) | yes: tokens 426296 > 400000 | capped |
| irs-donee-matching | sol-6.1@codex | m3: 400k total tokens, 20 min, $0.6 | pass | 91 | 180173 | 17613 | 0.0783 |  | medium (medium) | no | finished |
| irs-donee-matching | sonnet-5-5@claude-code | m3: 400k total tokens, 20 min, $0.8 | pass | 45 | 193074 | 31256 | 0.1870 |  | medium (medium) | no | finished |
| irs-donee-matching | astra-6@codex | m3: 400k total tokens, 20 min, $1.2145 | pass | 84 | 184946 | 23282 | 0.5094 |  | medium (medium) | no | finished |
| irs-donee-matching | opus-5-5@claude-code | m3: 400k total tokens, 20 min, $1.5 | pass | 134 | 196142 | 50878 | 0.5190 |  | medium (medium) | no | finished |
| irs-donee-matching | opus+sonnet-team@claude-code | m4: 300k fresh tokens, 20 min, $2.4299 | pass | 157 | 471676 | 99842 | 0.7915 | 3 | medium (medium) | no | finished |
| irs-donee-matching | opus+haiku-swarm@claude-code | m4: 300k fresh tokens, 20 min, $3 | pass | 167 | 1146606 | 218785 | 0.9228 | 10 | medium (medium) | no | finished |

## mypy-deferred-alias-crash

| Task | Contestant | Cap profile | Result | Wall s | Total tokens | Fresh tokens | $ equiv | Workers | Effort (seen) | Cap reason | Finished or capped |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mypy-deferred-alias-crash | haiku-5-5@claude-code | m3: 400k total tokens, 20 min, $0.1 | capped | 94 | 401085 | 45138 | 0.0175 |  | medium (medium) | yes: tokens 401085 > 400000 | capped |
| mypy-deferred-alias-crash | haiku-5-5@claude-code | m4: 300k fresh tokens, 20 min, $0.3 | fail | 209 | 598868 | 59000 | 0.0237 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | sol-6.1@codex | m3: 400k total tokens, 20 min, $0.6 | capped | 96 | 431207 | 35431 | 0.1356 |  | medium (medium) | yes: tokens 431207 > 400000 | capped |
| mypy-deferred-alias-crash | sonnet-5-5@claude-code | m3: 400k total tokens, 20 min, $0.8 | fail | 51 | 148854 | 18167 | 0.1223 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | sol-6.1@codex | m4: 300k fresh tokens, 20 min, $1.2 | pass | 127 | 540237 | 39245 | 0.1596 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | opus-5-5@claude-code | m3: 400k total tokens, 20 min, $1.5 | pass | 174 | 256185 | 35651 | 0.4123 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | opus+haiku-swarm@claude-code | m3: 400k total tokens, 20 min, $1.5 | capped | 158 | 434166 | 94393 | 0.6219 | 13 | medium (medium) | yes: tokens 434166 > 400000 | capped |
| mypy-deferred-alias-crash | sonnet-5-5@claude-code | m4: 300k fresh tokens, 20 min, $1.5 | fail | 43 | 131266 | 17605 | 0.1160 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | astra-6@codex | m3: 400k total tokens, 20 min, $2 | capped | 112 | 438214 | 38470 | 0.9088 |  | medium (medium) | yes: tokens 438214 > 400000 | capped |
| mypy-deferred-alias-crash | opus+sonnet-team@claude-code | m3: 400k total tokens, 20 min, $2 | capped | 136 | 413449 | 76586 | 0.7135 | 3 | medium (medium) | yes: tokens 413449 > 400000 | capped |
| mypy-deferred-alias-crash | opus-5-5@claude-code | m4: 300k fresh tokens, 20 min, $3 | pass | 265 | 626464 | 53215 | 0.6694 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | opus+haiku-swarm@claude-code | m4: 300k fresh tokens, 20 min, $3 | pass | 250 | 593287 | 92082 | 0.7139 | 10 | medium (medium) | no | finished |
| mypy-deferred-alias-crash | astra-6@codex | m4: 1000k fresh tokens, 20 min, $1.4 | pass | 150 | 583984 | 42288 | 1.1259 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | opus+sonnet-team@claude-code | m4: 1000k fresh tokens, 20 min, $1.85 | pass | 222 | 594377 | 83419 | 0.8298 | 3 | medium (medium) | no | finished |

## removed-pilot-task

| Task | Contestant | Cap profile | Result | Wall s | Total tokens | Fresh tokens | $ equiv | Workers | Effort (seen) | Cap reason | Finished or capped |
|---|---|---|---|---|---|---|---|---|---|---|---|
| removed-pilot-task | haiku-5-5@claude-code | m2: 250k total tokens, 10 min, $0.03 | pass | 27 | 88138 | 19492 | 0.0060 |  | medium (medium) | no | finished |
| removed-pilot-task | haiku-5-5@claude-code | m2: 250k total tokens, 10 min, $0.03 | pass | 30 | 130327 | 17759 | 0.0061 |  | medium (medium) | no | finished |
| removed-pilot-task | sol-6.1@codex | m2: 250k total tokens, 10 min, $0.3 | pass | 34 | 131191 | 10999 | 0.0440 |  | medium (medium) | no | finished |
| removed-pilot-task | sol-6.1@codex | m2: 250k total tokens, 10 min, $0.3 | pass | 37 | 155747 | 12515 | 0.0482 |  | medium (medium) | no | finished |
| removed-pilot-task | sonnet-5-5@claude-code | m2: 250k total tokens, 10 min, $0.4 | pass | 20 | 52328 | 9798 | 0.0585 |  | medium (medium) | no | finished |
| removed-pilot-task | sonnet-5-5@claude-code | m2: 250k total tokens, 10 min, $0.4 | pass | 16 | 50519 | 8721 | 0.0530 |  | medium (medium) | no | finished |
| removed-pilot-task | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | pass | 65 | 244215 | 59893 | 0.2809 | 10 | medium (medium) | no | finished |
| removed-pilot-task | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | pass | 89 | 350753 | 74523 | 0.4122 | 10 | medium (medium) | no | finished |
| removed-pilot-task | opus-5-5@claude-code | m2: 250k total tokens, 10 min, $0.75 | pass | 38 | 49758 | 12521 | 0.1448 |  | medium (medium) | no | finished |
| removed-pilot-task | opus-5-5@claude-code | m2: 250k total tokens, 10 min, $0.75 | pass | 38 | 51291 | 13817 | 0.1575 |  | medium (medium) | no | finished |
| removed-pilot-task | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 65 | 210750 | 42279 | 0.3440 | 3 | medium (medium) | no | finished |
| removed-pilot-task | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 60 | 165725 | 37962 | 0.3124 | 3 | medium (medium) | no | finished |
| removed-pilot-task | astra-6@codex | m2: 250k total tokens, 10 min, $1.5 | pass | 32 | 141409 | 9569 | 0.2659 |  | medium (medium) | no | finished |
| removed-pilot-task | astra-6@codex | m2: 250k total tokens, 10 min, $1.5 | pass | 32 | 156511 | 13023 | 0.3137 |  | medium (medium) | no | finished |

## taskiq-lazy-logging

| Task | Contestant | Cap profile | Result | Wall s | Total tokens | Fresh tokens | $ equiv | Workers | Effort (seen) | Cap reason | Finished or capped |
|---|---|---|---|---|---|---|---|---|---|---|---|
| taskiq-lazy-logging | haiku-5-5@claude-code | m2: 150k total tokens, 10 min, $0.03 | pass | 46 | 118408 | 22847 | 0.0075 |  | medium (medium) | no | finished |
| taskiq-lazy-logging | haiku-5-5@claude-code | m2: 150k total tokens, 10 min, $0.03 | capped | 34 | 156061 | 33314 | 0.0101 |  | medium (medium) | yes: tokens 156061 > 150000 | capped |
| taskiq-lazy-logging | sol-6.1@codex | m2: 150k total tokens, 10 min, $0.3 | capped | 53 | 151989 | 23733 | 0.0801 |  | medium (medium) | yes: tokens 151989 > 150000 | capped |
| taskiq-lazy-logging | sol-6.1@codex | m2: 150k total tokens, 10 min, $0.3 | capped | 45 | 152386 | 24898 | 0.0796 |  | medium (medium) | yes: tokens 152386 > 150000 | capped |
| taskiq-lazy-logging | sonnet-5-5@claude-code | m2: 150k total tokens, 10 min, $0.4 | pass | 48 | 90567 | 20276 | 0.1177 |  | medium (medium) | no | finished |
| taskiq-lazy-logging | sonnet-5-5@claude-code | m2: 150k total tokens, 10 min, $0.4 | pass | 38 | 86623 | 19469 | 0.1141 |  | medium (medium) | no | finished |
| taskiq-lazy-logging | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | capped | 65 | 412298 | 106617 | 0.3270 | 10 | medium (medium) | yes: tokens 412298 > 400000 | capped |
| taskiq-lazy-logging | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | capped | 69 | 409882 | 106044 | 0.4225 | 10 | medium (medium) | yes: tokens 409882 > 400000 | capped |
| taskiq-lazy-logging | opus-5-5@claude-code | m2: 150k total tokens, 10 min, $0.75 | pass | 78 | 148929 | 30582 | 0.3403 |  | medium (medium) | no | finished |
| taskiq-lazy-logging | opus-5-5@claude-code | m2: 150k total tokens, 10 min, $0.75 | capped | 64 | 166361 | 33578 | 0.3589 |  | medium (medium) | yes: tokens 166361 > 150000 | capped |
| taskiq-lazy-logging | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 91 | 379644 | 66146 | 0.5554 | 3 | medium (medium) | no | finished |
| taskiq-lazy-logging | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 77 | 356085 | 57320 | 0.4885 | 3 | medium (medium) | no | finished |
| taskiq-lazy-logging | astra-6@codex | m2: 150k total tokens, 10 min, $1.5 | capped | 49 | 161277 | 25341 | 0.4815 |  | medium (medium) | yes: tokens 161277 > 150000 | capped |
| taskiq-lazy-logging | astra-6@codex | m2: 150k total tokens, 10 min, $1.5 | capped | 51 | 152911 | 34255 | 0.5629 |  | medium (medium) | yes: tokens 152911 > 150000 | capped |

## werkzeug-apply-conditions

| Task | Contestant | Cap profile | Result | Wall s | Total tokens | Fresh tokens | $ equiv | Workers | Effort (seen) | Cap reason | Finished or capped |
|---|---|---|---|---|---|---|---|---|---|---|---|
| werkzeug-apply-conditions | haiku-5-5@claude-code | m3: 400k total tokens, 20 min, $0.1 | capped | 98 | 435107 | 78175 | 0.0261 |  | medium (medium) | yes: tokens 435107 > 400000 | capped |
| werkzeug-apply-conditions | haiku-5-5@claude-code | m4: 300k fresh tokens, 20 min, $0.3 | fail | 268 | 2131566 | 149430 | 0.0664 |  | medium (medium) | no | finished |
| werkzeug-apply-conditions | sol-6.1@codex | m3: 400k total tokens, 20 min, $0.6 | capped | 413 | 441246 | 60702 | 0.2447 |  | medium (medium) | yes: tokens 441246 > 400000 | capped |
| werkzeug-apply-conditions | sonnet-5-5@claude-code | m3: 400k total tokens, 20 min, $0.8 | capped | 120 | 433272 | 63030 | 0.4263 |  | medium (medium) | yes: tokens 433272 > 400000 | capped |
| werkzeug-apply-conditions | sol-6.1@codex | m4: 300k fresh tokens, 20 min, $1.2 | pass | 302 | 1247098 | 84346 | 0.3913 |  | medium (medium) | no | finished |
| werkzeug-apply-conditions | opus-5-5@claude-code | m3: 400k total tokens, 20 min, $1.5 | capped | 185 | 405391 | 77582 | 0.9397 |  | medium (medium) | yes: tokens 405391 > 400000 | capped |
| werkzeug-apply-conditions | opus+haiku-swarm@claude-code | m3: 400k total tokens, 20 min, $1.5 | capped | 128 | 401913 | 91394 | 0.3492 | 6 | medium (medium) | yes: tokens 401327 > 400000 | capped |
| werkzeug-apply-conditions | sonnet-5-5@claude-code | m4: 300k fresh tokens, 20 min, $1.5 | pass | 61 | 171454 | 35434 | 0.2213 |  | medium (medium) | no | finished |
| werkzeug-apply-conditions | opus+sonnet-team@claude-code | m4: 300k fresh tokens, 20 min, $1.6385 | pass | 237 | 998512 | 155377 | 1.2842 | 4 | medium (medium) | no | finished |
| werkzeug-apply-conditions | astra-6@codex | m3: 400k total tokens, 20 min, $2 | capped | 215 | 452646 | 56614 | 1.3230 |  | medium (medium) | yes: tokens 452646 > 400000 | capped |
| werkzeug-apply-conditions | opus+sonnet-team@claude-code | m3: 400k total tokens, 20 min, $2 | capped | 179 | 406471 | 97543 | 0.8464 | 4 | medium (medium) | yes: tokens 406394 > 400000 | capped |
| werkzeug-apply-conditions | opus-5-5@claude-code | m4: 300k fresh tokens, 20 min, $3 | pass | 278 | 705875 | 102425 | 1.2756 |  | medium (medium) | no | finished |
| werkzeug-apply-conditions | opus+haiku-swarm@claude-code | m4: 300k fresh tokens, 20 min, $3 | capped | 209 | 1400130 | 302140 | 0.9999 | 11 | medium (medium) | yes: fresh tokens 302087 > 300000 | capped |
| werkzeug-apply-conditions | astra-6@codex | m4: 1000k fresh tokens, 20 min, $1.49 | capped | 265 | 639073 | 56289 | 1.5159 |  | medium (medium) | yes: usd 1.5159 > 1.49 | capped |

## All runs

| Task | Contestant | Cap profile | Result | Wall s | Total tokens | Fresh tokens | $ equiv | Workers | Effort (seen) | Cap reason | Finished or capped |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fda-recalls-clean | haiku-5-5@claude-code | m2: 150k total tokens, 10 min, $0.03 | pass | 18 | 52896 | 15616 | 0.0047 |  | medium (medium) | no | finished |
| fda-recalls-clean | sol-6.1@codex | m2: 150k total tokens, 10 min, $0.3 | pass | 25 | 85836 | 12492 | 0.0419 |  | medium (medium) | no | finished |
| fda-recalls-clean | sonnet-5-5@claude-code | m2: 150k total tokens, 10 min, $0.4 | pass | 13 | 39830 | 7995 | 0.0469 |  | medium (medium) | no | finished |
| fda-recalls-clean | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | pass | 123 | 338705 | 111465 | 0.5681 | 10 | medium (medium) | no | finished |
| fda-recalls-clean | opus-5-5@claude-code | m2: 150k total tokens, 10 min, $0.75 | pass | 31 | 54313 | 16630 | 0.1786 |  | medium (medium) | no | finished |
| fda-recalls-clean | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 63 | 187778 | 49077 | 0.4205 | 3 | medium (medium) | no | finished |
| fda-recalls-clean | astra-6@codex | m2: 150k total tokens, 10 min, $1.5 | pass | 30 | 85253 | 18053 | 0.2917 |  | medium (medium) | no | finished |
| humanize-intcomma-overflow | haiku-5-5@claude-code | m2: 150k total tokens, 10 min, $0.03 | pass | 17 | 66170 | 15720 | 0.0047 |  | medium (medium) | no | finished |
| humanize-intcomma-overflow | haiku-5-5@claude-code | m2: 150k total tokens, 10 min, $0.03 | pass | 25 | 118077 | 17188 | 0.0058 |  | medium (medium) | no | finished |
| humanize-intcomma-overflow | sol-6.1@codex | m2: 150k total tokens, 10 min, $0.3 | pass | 32 | 113722 | 15546 | 0.0467 |  | medium (medium) | no | finished |
| humanize-intcomma-overflow | sol-6.1@codex | m2: 150k total tokens, 10 min, $0.3 | pass | 23 | 102855 | 14663 | 0.0442 |  | medium (medium) | no | finished |
| humanize-intcomma-overflow | sonnet-5-5@claude-code | m2: 150k total tokens, 10 min, $0.4 | pass | 21 | 51401 | 9880 | 0.0614 |  | medium (medium) | no | finished |
| humanize-intcomma-overflow | sonnet-5-5@claude-code | m2: 150k total tokens, 10 min, $0.4 | pass | 21 | 51250 | 11038 | 0.0666 |  | medium (medium) | no | finished |
| humanize-intcomma-overflow | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | pass | 68 | 296521 | 72678 | 0.3383 | 10 | medium (medium) | no | finished |
| humanize-intcomma-overflow | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | pass | 132 | 338379 | 89552 | 0.4876 | 10 | medium (medium) | no | finished |
| humanize-intcomma-overflow | opus-5-5@claude-code | m2: 150k total tokens, 10 min, $0.75 | pass | 81 | 123233 | 29472 | 0.3452 |  | medium (medium) | no | finished |
| humanize-intcomma-overflow | opus-5-5@claude-code | m2: 150k total tokens, 10 min, $0.75 | pass | 58 | 54442 | 17946 | 0.2146 |  | medium (medium) | no | finished |
| humanize-intcomma-overflow | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 48 | 191280 | 42542 | 0.3234 | 3 | medium (medium) | no | finished |
| humanize-intcomma-overflow | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 87 | 179881 | 63350 | 0.4436 | 3 | medium (medium) | no | finished |
| humanize-intcomma-overflow | astra-6@codex | m2: 150k total tokens, 10 min, $1.5 | pass | 28 | 124730 | 25786 | 0.3953 |  | medium (medium) | no | finished |
| humanize-intcomma-overflow | astra-6@codex | m2: 150k total tokens, 10 min, $1.5 | pass | 21 | 110565 | 22757 | 0.3406 |  | medium (medium) | no | finished |
| irs-donee-matching | haiku-5-5@claude-code | m3: 400k total tokens, 20 min, $0.1 | capped | 97 | 426296 | 72824 | 0.0238 |  | medium (medium) | yes: tokens 426296 > 400000 | capped |
| irs-donee-matching | sol-6.1@codex | m3: 400k total tokens, 20 min, $0.6 | pass | 91 | 180173 | 17613 | 0.0783 |  | medium (medium) | no | finished |
| irs-donee-matching | sonnet-5-5@claude-code | m3: 400k total tokens, 20 min, $0.8 | pass | 45 | 193074 | 31256 | 0.1870 |  | medium (medium) | no | finished |
| irs-donee-matching | astra-6@codex | m3: 400k total tokens, 20 min, $1.2145 | pass | 84 | 184946 | 23282 | 0.5094 |  | medium (medium) | no | finished |
| irs-donee-matching | opus-5-5@claude-code | m3: 400k total tokens, 20 min, $1.5 | pass | 134 | 196142 | 50878 | 0.5190 |  | medium (medium) | no | finished |
| irs-donee-matching | opus+sonnet-team@claude-code | m4: 300k fresh tokens, 20 min, $2.4299 | pass | 157 | 471676 | 99842 | 0.7915 | 3 | medium (medium) | no | finished |
| irs-donee-matching | opus+haiku-swarm@claude-code | m4: 300k fresh tokens, 20 min, $3 | pass | 167 | 1146606 | 218785 | 0.9228 | 10 | medium (medium) | no | finished |
| mypy-deferred-alias-crash | haiku-5-5@claude-code | m3: 400k total tokens, 20 min, $0.1 | capped | 94 | 401085 | 45138 | 0.0175 |  | medium (medium) | yes: tokens 401085 > 400000 | capped |
| mypy-deferred-alias-crash | haiku-5-5@claude-code | m4: 300k fresh tokens, 20 min, $0.3 | fail | 209 | 598868 | 59000 | 0.0237 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | sol-6.1@codex | m3: 400k total tokens, 20 min, $0.6 | capped | 96 | 431207 | 35431 | 0.1356 |  | medium (medium) | yes: tokens 431207 > 400000 | capped |
| mypy-deferred-alias-crash | sonnet-5-5@claude-code | m3: 400k total tokens, 20 min, $0.8 | fail | 51 | 148854 | 18167 | 0.1223 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | sol-6.1@codex | m4: 300k fresh tokens, 20 min, $1.2 | pass | 127 | 540237 | 39245 | 0.1596 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | opus-5-5@claude-code | m3: 400k total tokens, 20 min, $1.5 | pass | 174 | 256185 | 35651 | 0.4123 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | opus+haiku-swarm@claude-code | m3: 400k total tokens, 20 min, $1.5 | capped | 158 | 434166 | 94393 | 0.6219 | 13 | medium (medium) | yes: tokens 434166 > 400000 | capped |
| mypy-deferred-alias-crash | sonnet-5-5@claude-code | m4: 300k fresh tokens, 20 min, $1.5 | fail | 43 | 131266 | 17605 | 0.1160 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | astra-6@codex | m3: 400k total tokens, 20 min, $2 | capped | 112 | 438214 | 38470 | 0.9088 |  | medium (medium) | yes: tokens 438214 > 400000 | capped |
| mypy-deferred-alias-crash | opus+sonnet-team@claude-code | m3: 400k total tokens, 20 min, $2 | capped | 136 | 413449 | 76586 | 0.7135 | 3 | medium (medium) | yes: tokens 413449 > 400000 | capped |
| mypy-deferred-alias-crash | opus-5-5@claude-code | m4: 300k fresh tokens, 20 min, $3 | pass | 265 | 626464 | 53215 | 0.6694 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | opus+haiku-swarm@claude-code | m4: 300k fresh tokens, 20 min, $3 | pass | 250 | 593287 | 92082 | 0.7139 | 10 | medium (medium) | no | finished |
| removed-pilot-task | haiku-5-5@claude-code | m2: 250k total tokens, 10 min, $0.03 | pass | 27 | 88138 | 19492 | 0.0060 |  | medium (medium) | no | finished |
| removed-pilot-task | haiku-5-5@claude-code | m2: 250k total tokens, 10 min, $0.03 | pass | 30 | 130327 | 17759 | 0.0061 |  | medium (medium) | no | finished |
| removed-pilot-task | sol-6.1@codex | m2: 250k total tokens, 10 min, $0.3 | pass | 34 | 131191 | 10999 | 0.0440 |  | medium (medium) | no | finished |
| removed-pilot-task | sol-6.1@codex | m2: 250k total tokens, 10 min, $0.3 | pass | 37 | 155747 | 12515 | 0.0482 |  | medium (medium) | no | finished |
| removed-pilot-task | sonnet-5-5@claude-code | m2: 250k total tokens, 10 min, $0.4 | pass | 20 | 52328 | 9798 | 0.0585 |  | medium (medium) | no | finished |
| removed-pilot-task | sonnet-5-5@claude-code | m2: 250k total tokens, 10 min, $0.4 | pass | 16 | 50519 | 8721 | 0.0530 |  | medium (medium) | no | finished |
| removed-pilot-task | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | pass | 65 | 244215 | 59893 | 0.2809 | 10 | medium (medium) | no | finished |
| removed-pilot-task | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | pass | 89 | 350753 | 74523 | 0.4122 | 10 | medium (medium) | no | finished |
| removed-pilot-task | opus-5-5@claude-code | m2: 250k total tokens, 10 min, $0.75 | pass | 38 | 49758 | 12521 | 0.1448 |  | medium (medium) | no | finished |
| removed-pilot-task | opus-5-5@claude-code | m2: 250k total tokens, 10 min, $0.75 | pass | 38 | 51291 | 13817 | 0.1575 |  | medium (medium) | no | finished |
| removed-pilot-task | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 65 | 210750 | 42279 | 0.3440 | 3 | medium (medium) | no | finished |
| removed-pilot-task | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 60 | 165725 | 37962 | 0.3124 | 3 | medium (medium) | no | finished |
| removed-pilot-task | astra-6@codex | m2: 250k total tokens, 10 min, $1.5 | pass | 32 | 141409 | 9569 | 0.2659 |  | medium (medium) | no | finished |
| removed-pilot-task | astra-6@codex | m2: 250k total tokens, 10 min, $1.5 | pass | 32 | 156511 | 13023 | 0.3137 |  | medium (medium) | no | finished |
| taskiq-lazy-logging | haiku-5-5@claude-code | m2: 150k total tokens, 10 min, $0.03 | pass | 46 | 118408 | 22847 | 0.0075 |  | medium (medium) | no | finished |
| taskiq-lazy-logging | haiku-5-5@claude-code | m2: 150k total tokens, 10 min, $0.03 | capped | 34 | 156061 | 33314 | 0.0101 |  | medium (medium) | yes: tokens 156061 > 150000 | capped |
| taskiq-lazy-logging | sol-6.1@codex | m2: 150k total tokens, 10 min, $0.3 | capped | 53 | 151989 | 23733 | 0.0801 |  | medium (medium) | yes: tokens 151989 > 150000 | capped |
| taskiq-lazy-logging | sol-6.1@codex | m2: 150k total tokens, 10 min, $0.3 | capped | 45 | 152386 | 24898 | 0.0796 |  | medium (medium) | yes: tokens 152386 > 150000 | capped |
| taskiq-lazy-logging | sonnet-5-5@claude-code | m2: 150k total tokens, 10 min, $0.4 | pass | 48 | 90567 | 20276 | 0.1177 |  | medium (medium) | no | finished |
| taskiq-lazy-logging | sonnet-5-5@claude-code | m2: 150k total tokens, 10 min, $0.4 | pass | 38 | 86623 | 19469 | 0.1141 |  | medium (medium) | no | finished |
| taskiq-lazy-logging | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | capped | 65 | 412298 | 106617 | 0.3270 | 10 | medium (medium) | yes: tokens 412298 > 400000 | capped |
| taskiq-lazy-logging | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | capped | 69 | 409882 | 106044 | 0.4225 | 10 | medium (medium) | yes: tokens 409882 > 400000 | capped |
| taskiq-lazy-logging | opus-5-5@claude-code | m2: 150k total tokens, 10 min, $0.75 | pass | 78 | 148929 | 30582 | 0.3403 |  | medium (medium) | no | finished |
| taskiq-lazy-logging | opus-5-5@claude-code | m2: 150k total tokens, 10 min, $0.75 | capped | 64 | 166361 | 33578 | 0.3589 |  | medium (medium) | yes: tokens 166361 > 150000 | capped |
| taskiq-lazy-logging | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 91 | 379644 | 66146 | 0.5554 | 3 | medium (medium) | no | finished |
| taskiq-lazy-logging | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 77 | 356085 | 57320 | 0.4885 | 3 | medium (medium) | no | finished |
| taskiq-lazy-logging | astra-6@codex | m2: 150k total tokens, 10 min, $1.5 | capped | 49 | 161277 | 25341 | 0.4815 |  | medium (medium) | yes: tokens 161277 > 150000 | capped |
| taskiq-lazy-logging | astra-6@codex | m2: 150k total tokens, 10 min, $1.5 | capped | 51 | 152911 | 34255 | 0.5629 |  | medium (medium) | yes: tokens 152911 > 150000 | capped |
| werkzeug-apply-conditions | haiku-5-5@claude-code | m3: 400k total tokens, 20 min, $0.1 | capped | 98 | 435107 | 78175 | 0.0261 |  | medium (medium) | yes: tokens 435107 > 400000 | capped |
| werkzeug-apply-conditions | haiku-5-5@claude-code | m4: 300k fresh tokens, 20 min, $0.3 | fail | 268 | 2131566 | 149430 | 0.0664 |  | medium (medium) | no | finished |
| werkzeug-apply-conditions | sol-6.1@codex | m3: 400k total tokens, 20 min, $0.6 | capped | 413 | 441246 | 60702 | 0.2447 |  | medium (medium) | yes: tokens 441246 > 400000 | capped |
| werkzeug-apply-conditions | sonnet-5-5@claude-code | m3: 400k total tokens, 20 min, $0.8 | capped | 120 | 433272 | 63030 | 0.4263 |  | medium (medium) | yes: tokens 433272 > 400000 | capped |
| werkzeug-apply-conditions | sol-6.1@codex | m4: 300k fresh tokens, 20 min, $1.2 | pass | 302 | 1247098 | 84346 | 0.3913 |  | medium (medium) | no | finished |
| werkzeug-apply-conditions | opus-5-5@claude-code | m3: 400k total tokens, 20 min, $1.5 | capped | 185 | 405391 | 77582 | 0.9397 |  | medium (medium) | yes: tokens 405391 > 400000 | capped |
| werkzeug-apply-conditions | opus+haiku-swarm@claude-code | m3: 400k total tokens, 20 min, $1.5 | capped | 128 | 401913 | 91394 | 0.3492 | 6 | medium (medium) | yes: tokens 401327 > 400000 | capped |
| werkzeug-apply-conditions | sonnet-5-5@claude-code | m4: 300k fresh tokens, 20 min, $1.5 | pass | 61 | 171454 | 35434 | 0.2213 |  | medium (medium) | no | finished |
| werkzeug-apply-conditions | opus+sonnet-team@claude-code | m4: 300k fresh tokens, 20 min, $1.6385 | pass | 237 | 998512 | 155377 | 1.2842 | 4 | medium (medium) | no | finished |
| werkzeug-apply-conditions | astra-6@codex | m3: 400k total tokens, 20 min, $2 | capped | 215 | 452646 | 56614 | 1.3230 |  | medium (medium) | yes: tokens 452646 > 400000 | capped |
| werkzeug-apply-conditions | opus+sonnet-team@claude-code | m3: 400k total tokens, 20 min, $2 | capped | 179 | 406471 | 97543 | 0.8464 | 4 | medium (medium) | yes: tokens 406394 > 400000 | capped |
| werkzeug-apply-conditions | opus-5-5@claude-code | m4: 300k fresh tokens, 20 min, $3 | pass | 278 | 705875 | 102425 | 1.2756 |  | medium (medium) | no | finished |
| werkzeug-apply-conditions | opus+haiku-swarm@claude-code | m4: 300k fresh tokens, 20 min, $3 | capped | 209 | 1400130 | 302140 | 0.9999 | 11 | medium (medium) | yes: fresh tokens 302087 > 300000 | capped |
| werkzeug-apply-conditions | astra-6@codex | m4: 1000k fresh tokens, 20 min, $1.49 | capped | 265 | 639073 | 56289 | 1.5159 |  | medium (medium) | yes: usd 1.5159 > 1.49 | capped |
| mypy-deferred-alias-crash | astra-6@codex | m4: 1000k fresh tokens, 20 min, $1.4 | pass | 150 | 583984 | 42288 | 1.1259 |  | medium (medium) | no | finished |
| mypy-deferred-alias-crash | opus+sonnet-team@claude-code | m4: 1000k fresh tokens, 20 min, $1.85 | pass | 222 | 594377 | 83419 | 0.8298 | 3 | medium (medium) | no | finished |
