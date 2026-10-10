## Leaderboard, M4 rerun: cap on fresh tokens (300k), dollars and minutes

| # | Contestant | Passed | Work passes the check | $ spent | $ per solved run | Mean wall s | Mean total tokens | Mean fresh tokens | Max workers | Capped |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Sol 6.1 · Codex | 2/2 | 2/2 | $0.55 | $0.28 | 214 | 893,668 | 61,796 |  | 0 |
| 2 | Opus 5.5 · Claude Code | 2/2 | 2/2 | $1.95 | $0.97 | 271 | 666,170 | 77,820 |  | 0 |
| 3 | Opus + Sonnet team · Claude Code | 2/2 | 2/2 | $2.08 | $1.04 | 197 | 735,094 | 127,610 | 4 | 0 |
| 4 | Opus + Haiku swarm · Claude Code | 2/3 | 3/3 | $2.64 | $1.32 | 209 | 1,046,674 | 204,336 | 11 | 1 |
| 5 | Sonnet 5.5 · Claude Code | 1/2 | 1/2 | $0.34 | $0.34 | 52 | 151,360 | 26,520 |  | 0 |
| 6 | Haiku 5.5 · Claude Code | 0/2 | 0/2 | $0.090 | n/a | 238 | 1,365,217 | 104,215 |  | 0 |

## Leaderboard, Pilot and M3: cap on total tokens (cache reads included), dollars and minutes

| # | Contestant | Passed | Work passes the check | $ spent | $ per solved run | Mean wall s | Mean total tokens | Mean fresh tokens | Max workers | Capped |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Sonnet 5.5 · Claude Code | 8/10 | 9/10 | $1.25 | $0.16 | 39 | 119,772 | 19,963 |  | 1 |
| 2 | Opus 5.5 · Claude Code | 8/10 | 10/10 | $3.61 | $0.45 | 88 | 150,604 | 31,866 |  | 2 |
| 3 | Opus + Sonnet team · Claude Code | 7/9 | 9/9 | $4.45 | $0.64 | 90 | 276,785 | 59,201 | 4 | 2 |
| 4 | Haiku 5.5 · Claude Code | 6/10 | 7/10 | $0.11 | $0.019 | 48 | 199,256 | 33,807 |  | 4 |
| 5 | Sol 6.1 · Codex | 6/10 | 10/10 | $0.84 | $0.14 | 85 | 194,635 | 22,859 |  | 4 |
| 6 | Astra 6 · Codex | 6/10 | 10/10 | $5.39 | $0.90 | 65 | 200,846 | 26,715 |  | 4 |
| 7 | Opus + Haiku swarm · Claude Code | 5/9 | 6/9 | $3.81 | $0.76 | 100 | 358,537 | 89,618 | 13 | 4 |

## M3 against M4 (same tasks, two cap profiles)

m3 = cap of 400k total tokens (cache reads included); m4 = cap of 300k fresh tokens (input, cache writes, output). One run per cell. "not run" = the cell was not run (spend ledger stopped the matrix).

| Task | Contestant | Cap profile | Result | Work passes check | $ | Wall s | Fresh tokens | Total tokens |
|---|---|---|---|---|---|---|---|---|
| mypy-deferred-alias-crash | Astra 6 · Codex | m3 | capped | yes | $0.91 | 112 | 38,470 | 438,214 |
| mypy-deferred-alias-crash | Astra 6 · Codex | m4 | not run |  |  |  |  |  |
| mypy-deferred-alias-crash | Haiku 5.5 · Claude Code | m3 | capped | no | $0.017 | 94 | 45,138 | 401,085 |
| mypy-deferred-alias-crash | Haiku 5.5 · Claude Code | m4 | fail | no | $0.024 | 209 | 59,000 | 598,868 |
| mypy-deferred-alias-crash | Opus + Haiku swarm · Claude Code | m3 | capped | yes | $0.62 | 158 | 94,393 | 434,166 |
| mypy-deferred-alias-crash | Opus + Haiku swarm · Claude Code | m4 | pass | yes | $0.71 | 250 | 92,082 | 593,287 |
| mypy-deferred-alias-crash | Opus + Sonnet team · Claude Code | m3 | capped | yes | $0.71 | 136 | 76,586 | 413,449 |
| mypy-deferred-alias-crash | Opus + Sonnet team · Claude Code | m4 | not run |  |  |  |  |  |
| mypy-deferred-alias-crash | Opus 5.5 · Claude Code | m3 | pass | yes | $0.41 | 174 | 35,651 | 256,185 |
| mypy-deferred-alias-crash | Opus 5.5 · Claude Code | m4 | pass | yes | $0.67 | 265 | 53,215 | 626,464 |
| mypy-deferred-alias-crash | Sol 6.1 · Codex | m3 | capped | yes | $0.14 | 96 | 35,431 | 431,207 |
| mypy-deferred-alias-crash | Sol 6.1 · Codex | m4 | pass | yes | $0.16 | 127 | 39,245 | 540,237 |
| mypy-deferred-alias-crash | Sonnet 5.5 · Claude Code | m3 | fail | no | $0.12 | 51 | 18,167 | 148,854 |
| mypy-deferred-alias-crash | Sonnet 5.5 · Claude Code | m4 | fail | no | $0.12 | 43 | 17,605 | 131,266 |
| werkzeug-apply-conditions | Astra 6 · Codex | m3 | capped | yes | $1.32 | 215 | 56,614 | 452,646 |
| werkzeug-apply-conditions | Astra 6 · Codex | m4 | not run |  |  |  |  |  |
| werkzeug-apply-conditions | Haiku 5.5 · Claude Code | m3 | capped | no | $0.026 | 98 | 78,175 | 435,107 |
| werkzeug-apply-conditions | Haiku 5.5 · Claude Code | m4 | fail | no | $0.066 | 268 | 149,430 | 2,131,566 |
| werkzeug-apply-conditions | Opus + Haiku swarm · Claude Code | m3 | capped | no | $0.35 | 128 | 91,394 | 401,913 |
| werkzeug-apply-conditions | Opus + Haiku swarm · Claude Code | m4 | capped | yes | $1.00 | 209 | 302,140 | 1,400,130 |
| werkzeug-apply-conditions | Opus + Sonnet team · Claude Code | m3 | capped | yes | $0.85 | 179 | 97,543 | 406,471 |
| werkzeug-apply-conditions | Opus + Sonnet team · Claude Code | m4 | pass | yes | $1.28 | 237 | 155,377 | 998,512 |
| werkzeug-apply-conditions | Opus 5.5 · Claude Code | m3 | capped | yes | $0.94 | 185 | 77,582 | 405,391 |
| werkzeug-apply-conditions | Opus 5.5 · Claude Code | m4 | pass | yes | $1.28 | 278 | 102,425 | 705,875 |
| werkzeug-apply-conditions | Sol 6.1 · Codex | m3 | capped | yes | $0.24 | 413 | 60,702 | 441,246 |
| werkzeug-apply-conditions | Sol 6.1 · Codex | m4 | pass | yes | $0.39 | 302 | 84,346 | 1,247,098 |
| werkzeug-apply-conditions | Sonnet 5.5 · Claude Code | m3 | capped | yes | $0.43 | 120 | 63,030 | 433,272 |
| werkzeug-apply-conditions | Sonnet 5.5 · Claude Code | m4 | pass | yes | $0.22 | 61 | 35,434 | 171,454 |

## fda-recalls-clean

| Contestant | Cap profile | Passed | Work passes the check | Mean $ | Mean wall s | Mean total tokens | Mean fresh tokens | Workers | Capped |
|---|---|---|---|---|---|---|---|---|---|
| Haiku 5.5 · Claude Code | m2 | 1/1 | 1/1 | $0.005 | 18 | 52,896 | 15,616 |  |  |
| Sol 6.1 · Codex | m2 | 1/1 | 1/1 | $0.042 | 25 | 85,836 | 12,492 |  |  |
| Sonnet 5.5 · Claude Code | m2 | 1/1 | 1/1 | $0.047 | 13 | 39,830 | 7,995 |  |  |
| Opus 5.5 · Claude Code | m2 | 1/1 | 1/1 | $0.18 | 31 | 54,313 | 16,630 |  |  |
| Astra 6 · Codex | m2 | 1/1 | 1/1 | $0.29 | 30 | 85,253 | 18,053 |  |  |
| Opus + Sonnet team · Claude Code | m2 | 1/1 | 1/1 | $0.42 | 63 | 187,778 | 49,077 | 3 |  |
| Opus + Haiku swarm · Claude Code | m2 | 1/1 | 1/1 | $0.57 | 123 | 338,705 | 111,465 | 10 |  |

## humanize-intcomma-overflow

| Contestant | Cap profile | Passed | Work passes the check | Mean $ | Mean wall s | Mean total tokens | Mean fresh tokens | Workers | Capped |
|---|---|---|---|---|---|---|---|---|---|
| Haiku 5.5 · Claude Code | m2 | 2/2 | 2/2 | $0.005 | 21 | 92,124 | 16,454 |  |  |
| Sol 6.1 · Codex | m2 | 2/2 | 2/2 | $0.045 | 27 | 108,288 | 15,104 |  |  |
| Sonnet 5.5 · Claude Code | m2 | 2/2 | 2/2 | $0.064 | 21 | 51,326 | 10,459 |  |  |
| Opus 5.5 · Claude Code | m2 | 2/2 | 2/2 | $0.28 | 69 | 88,838 | 23,709 |  |  |
| Astra 6 · Codex | m2 | 2/2 | 2/2 | $0.37 | 24 | 117,648 | 24,272 |  |  |
| Opus + Sonnet team · Claude Code | m2 | 2/2 | 2/2 | $0.38 | 68 | 185,580 | 52,946 | 3 |  |
| Opus + Haiku swarm · Claude Code | m2 | 2/2 | 2/2 | $0.41 | 100 | 317,450 | 81,115 | 10 |  |

## irs-donee-matching

| Contestant | Cap profile | Passed | Work passes the check | Mean $ | Mean wall s | Mean total tokens | Mean fresh tokens | Workers | Capped |
|---|---|---|---|---|---|---|---|---|---|
| Sol 6.1 · Codex | m3 | 1/1 | 1/1 | $0.078 | 91 | 180,173 | 17,613 |  |  |
| Sonnet 5.5 · Claude Code | m3 | 1/1 | 1/1 | $0.19 | 45 | 193,074 | 31,256 |  |  |
| Astra 6 · Codex | m3 | 1/1 | 1/1 | $0.51 | 84 | 184,946 | 23,282 |  |  |
| Opus 5.5 · Claude Code | m3 | 1/1 | 1/1 | $0.52 | 134 | 196,142 | 50,878 |  |  |
| Haiku 5.5 · Claude Code | m3 | 0/1 | 1/1 | $0.024 | 97 | 426,296 | 72,824 |  | 1 |
| Opus + Sonnet team · Claude Code | m4 | 1/1 | 1/1 | $0.79 | 157 | 471,676 | 99,842 | 3 |  |
| Opus + Haiku swarm · Claude Code | m4 | 1/1 | 1/1 | $0.92 | 167 | 1,146,606 | 218,785 | 10 |  |

## mypy-deferred-alias-crash

| Contestant | Cap profile | Passed | Work passes the check | Mean $ | Mean wall s | Mean total tokens | Mean fresh tokens | Workers | Capped |
|---|---|---|---|---|---|---|---|---|---|
| Opus 5.5 · Claude Code | m3 | 1/1 | 1/1 | $0.41 | 174 | 256,185 | 35,651 |  |  |
| Haiku 5.5 · Claude Code | m3 | 0/1 | 0/1 | $0.017 | 94 | 401,085 | 45,138 |  | 1 |
| Sonnet 5.5 · Claude Code | m3 | 0/1 | 0/1 | $0.12 | 51 | 148,854 | 18,167 |  |  |
| Sol 6.1 · Codex | m3 | 0/1 | 1/1 | $0.14 | 96 | 431,207 | 35,431 |  | 1 |
| Opus + Haiku swarm · Claude Code | m3 | 0/1 | 1/1 | $0.62 | 158 | 434,166 | 94,393 | 13 | 1 |
| Opus + Sonnet team · Claude Code | m3 | 0/1 | 1/1 | $0.71 | 136 | 413,449 | 76,586 | 3 | 1 |
| Astra 6 · Codex | m3 | 0/1 | 1/1 | $0.91 | 112 | 438,214 | 38,470 |  | 1 |
| Sol 6.1 · Codex | m4 | 1/1 | 1/1 | $0.16 | 127 | 540,237 | 39,245 |  |  |
| Opus 5.5 · Claude Code | m4 | 1/1 | 1/1 | $0.67 | 265 | 626,464 | 53,215 |  |  |
| Opus + Haiku swarm · Claude Code | m4 | 1/1 | 1/1 | $0.71 | 250 | 593,287 | 92,082 | 10 |  |
| Haiku 5.5 · Claude Code | m4 | 0/1 | 0/1 | $0.024 | 209 | 598,868 | 59,000 |  |  |
| Sonnet 5.5 · Claude Code | m4 | 0/1 | 0/1 | $0.12 | 43 | 131,266 | 17,605 |  |  |

## removed-pilot-task

| Contestant | Cap profile | Passed | Work passes the check | Mean $ | Mean wall s | Mean total tokens | Mean fresh tokens | Workers | Capped |
|---|---|---|---|---|---|---|---|---|---|
| Haiku 5.5 · Claude Code | m2 | 2/2 | 2/2 | $0.006 | 28 | 109,232 | 18,626 |  |  |
| Sol 6.1 · Codex | m2 | 2/2 | 2/2 | $0.046 | 36 | 143,469 | 11,757 |  |  |
| Sonnet 5.5 · Claude Code | m2 | 2/2 | 2/2 | $0.056 | 18 | 51,424 | 9,260 |  |  |
| Opus 5.5 · Claude Code | m2 | 2/2 | 2/2 | $0.15 | 38 | 50,524 | 13,169 |  |  |
| Astra 6 · Codex | m2 | 2/2 | 2/2 | $0.29 | 32 | 148,960 | 11,296 |  |  |
| Opus + Sonnet team · Claude Code | m2 | 2/2 | 2/2 | $0.33 | 62 | 188,238 | 40,120 | 3 |  |
| Opus + Haiku swarm · Claude Code | m2 | 2/2 | 2/2 | $0.35 | 77 | 297,484 | 67,208 | 10 |  |

## taskiq-lazy-logging

| Contestant | Cap profile | Passed | Work passes the check | Mean $ | Mean wall s | Mean total tokens | Mean fresh tokens | Workers | Capped |
|---|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 · Claude Code | m2 | 2/2 | 2/2 | $0.12 | 43 | 88,595 | 19,872 |  |  |
| Opus + Sonnet team · Claude Code | m2 | 2/2 | 2/2 | $0.52 | 84 | 367,864 | 61,733 | 3 |  |
| Haiku 5.5 · Claude Code | m2 | 1/2 | 1/2 | $0.009 | 40 | 137,234 | 28,080 |  | 1 |
| Opus 5.5 · Claude Code | m2 | 1/2 | 2/2 | $0.35 | 71 | 157,645 | 32,080 |  | 1 |
| Sol 6.1 · Codex | m2 | 0/2 | 2/2 | $0.080 | 49 | 152,188 | 24,316 |  | 2 |
| Opus + Haiku swarm · Claude Code | m2 | 0/2 | 0/2 | $0.37 | 67 | 411,090 | 106,330 | 10 | 2 |
| Astra 6 · Codex | m2 | 0/2 | 2/2 | $0.52 | 50 | 157,094 | 29,798 |  | 2 |

## werkzeug-apply-conditions

| Contestant | Cap profile | Passed | Work passes the check | Mean $ | Mean wall s | Mean total tokens | Mean fresh tokens | Workers | Capped |
|---|---|---|---|---|---|---|---|---|---|
| Haiku 5.5 · Claude Code | m3 | 0/1 | 0/1 | $0.026 | 98 | 435,107 | 78,175 |  | 1 |
| Sol 6.1 · Codex | m3 | 0/1 | 1/1 | $0.24 | 413 | 441,246 | 60,702 |  | 1 |
| Opus + Haiku swarm · Claude Code | m3 | 0/1 | 0/1 | $0.35 | 128 | 401,913 | 91,394 | 6 | 1 |
| Sonnet 5.5 · Claude Code | m3 | 0/1 | 1/1 | $0.43 | 120 | 433,272 | 63,030 |  | 1 |
| Opus + Sonnet team · Claude Code | m3 | 0/1 | 1/1 | $0.85 | 179 | 406,471 | 97,543 | 4 | 1 |
| Opus 5.5 · Claude Code | m3 | 0/1 | 1/1 | $0.94 | 185 | 405,391 | 77,582 |  | 1 |
| Astra 6 · Codex | m3 | 0/1 | 1/1 | $1.32 | 215 | 452,646 | 56,614 |  | 1 |
| Sonnet 5.5 · Claude Code | m4 | 1/1 | 1/1 | $0.22 | 61 | 171,454 | 35,434 |  |  |
| Sol 6.1 · Codex | m4 | 1/1 | 1/1 | $0.39 | 302 | 1,247,098 | 84,346 |  |  |
| Opus 5.5 · Claude Code | m4 | 1/1 | 1/1 | $1.28 | 278 | 705,875 | 102,425 |  |  |
| Opus + Sonnet team · Claude Code | m4 | 1/1 | 1/1 | $1.28 | 237 | 998,512 | 155,377 | 4 |  |
| Haiku 5.5 · Claude Code | m4 | 0/1 | 0/1 | $0.066 | 268 | 2,131,566 | 149,430 |  |  |
| Opus + Haiku swarm · Claude Code | m4 | 0/1 | 1/1 | $1.00 | 209 | 1,400,130 | 302,140 | 11 | 1 |

## All runs

| Task | Contestant | Cap profile | Result | Wall s | Total tokens | Fresh tokens | $ equiv | Workers | Effort (seen) | Capped |
|---|---|---|---|---|---|---|---|---|---|---|
| fda-recalls-clean | haiku-5-5@claude-code | m2: 150k total tokens, 10 min, $0.03 | pass | 18 | 52,896 | 15,616 | $0.0047 |  | medium (medium) | no |
| fda-recalls-clean | sol-6.1@codex | m2: 150k total tokens, 10 min, $0.3 | pass | 25 | 85,836 | 12,492 | $0.0419 |  | medium (medium) | no |
| fda-recalls-clean | sonnet-5-5@claude-code | m2: 150k total tokens, 10 min, $0.4 | pass | 13 | 39,830 | 7,995 | $0.0469 |  | medium (medium) | no |
| fda-recalls-clean | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | pass | 123 | 338,705 | 111,465 | $0.5681 | 10 | medium (medium) | no |
| fda-recalls-clean | opus-5-5@claude-code | m2: 150k total tokens, 10 min, $0.75 | pass | 31 | 54,313 | 16,630 | $0.1786 |  | medium (medium) | no |
| fda-recalls-clean | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 63 | 187,778 | 49,077 | $0.4205 | 3 | medium (medium) | no |
| fda-recalls-clean | astra-6@codex | m2: 150k total tokens, 10 min, $1.5 | pass | 30 | 85,253 | 18,053 | $0.2917 |  | medium (medium) | no |
| humanize-intcomma-overflow | haiku-5-5@claude-code | m2: 150k total tokens, 10 min, $0.03 | pass | 17 | 66,170 | 15,720 | $0.0047 |  | medium (medium) | no |
| humanize-intcomma-overflow | haiku-5-5@claude-code | m2: 150k total tokens, 10 min, $0.03 | pass | 25 | 118,077 | 17,188 | $0.0058 |  | medium (medium) | no |
| humanize-intcomma-overflow | sol-6.1@codex | m2: 150k total tokens, 10 min, $0.3 | pass | 32 | 113,722 | 15,546 | $0.0467 |  | medium (medium) | no |
| humanize-intcomma-overflow | sol-6.1@codex | m2: 150k total tokens, 10 min, $0.3 | pass | 23 | 102,855 | 14,663 | $0.0442 |  | medium (medium) | no |
| humanize-intcomma-overflow | sonnet-5-5@claude-code | m2: 150k total tokens, 10 min, $0.4 | pass | 21 | 51,401 | 9,880 | $0.0614 |  | medium (medium) | no |
| humanize-intcomma-overflow | sonnet-5-5@claude-code | m2: 150k total tokens, 10 min, $0.4 | pass | 21 | 51,250 | 11,038 | $0.0666 |  | medium (medium) | no |
| humanize-intcomma-overflow | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | pass | 68 | 296,521 | 72,678 | $0.3383 | 10 | medium (medium) | no |
| humanize-intcomma-overflow | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | pass | 132 | 338,379 | 89,552 | $0.4876 | 10 | medium (medium) | no |
| humanize-intcomma-overflow | opus-5-5@claude-code | m2: 150k total tokens, 10 min, $0.75 | pass | 81 | 123,233 | 29,472 | $0.3452 |  | medium (medium) | no |
| humanize-intcomma-overflow | opus-5-5@claude-code | m2: 150k total tokens, 10 min, $0.75 | pass | 58 | 54,442 | 17,946 | $0.2146 |  | medium (medium) | no |
| humanize-intcomma-overflow | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 48 | 191,280 | 42,542 | $0.3234 | 3 | medium (medium) | no |
| humanize-intcomma-overflow | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 87 | 179,881 | 63,350 | $0.4436 | 3 | medium (medium) | no |
| humanize-intcomma-overflow | astra-6@codex | m2: 150k total tokens, 10 min, $1.5 | pass | 28 | 124,730 | 25,786 | $0.3953 |  | medium (medium) | no |
| humanize-intcomma-overflow | astra-6@codex | m2: 150k total tokens, 10 min, $1.5 | pass | 21 | 110,565 | 22,757 | $0.3406 |  | medium (medium) | no |
| irs-donee-matching | haiku-5-5@claude-code | m3: 400k total tokens, 20 min, $0.1 | capped | 97 | 426,296 | 72,824 | $0.0238 |  | medium (medium) | yes: tokens 426296 > 400000 |
| irs-donee-matching | sol-6.1@codex | m3: 400k total tokens, 20 min, $0.6 | pass | 91 | 180,173 | 17,613 | $0.0783 |  | medium (medium) | no |
| irs-donee-matching | sonnet-5-5@claude-code | m3: 400k total tokens, 20 min, $0.8 | pass | 45 | 193,074 | 31,256 | $0.1870 |  | medium (medium) | no |
| irs-donee-matching | astra-6@codex | m3: 400k total tokens, 20 min, $1.2145 | pass | 84 | 184,946 | 23,282 | $0.5094 |  | medium (medium) | no |
| irs-donee-matching | opus-5-5@claude-code | m3: 400k total tokens, 20 min, $1.5 | pass | 134 | 196,142 | 50,878 | $0.5190 |  | medium (medium) | no |
| irs-donee-matching | opus+sonnet-team@claude-code | m4: 300k fresh tokens, 20 min, $2.4299 | pass | 157 | 471,676 | 99,842 | $0.7915 | 3 | medium (medium) | no |
| irs-donee-matching | opus+haiku-swarm@claude-code | m4: 300k fresh tokens, 20 min, $3 | pass | 167 | 1,146,606 | 218,785 | $0.9228 | 10 | medium (medium) | no |
| mypy-deferred-alias-crash | haiku-5-5@claude-code | m3: 400k total tokens, 20 min, $0.1 | capped | 94 | 401,085 | 45,138 | $0.0175 |  | medium (medium) | yes: tokens 401085 > 400000 |
| mypy-deferred-alias-crash | haiku-5-5@claude-code | m4: 300k fresh tokens, 20 min, $0.3 | fail | 209 | 598,868 | 59,000 | $0.0237 |  | medium (medium) | no |
| mypy-deferred-alias-crash | sol-6.1@codex | m3: 400k total tokens, 20 min, $0.6 | capped | 96 | 431,207 | 35,431 | $0.1356 |  | medium (medium) | yes: tokens 431207 > 400000 |
| mypy-deferred-alias-crash | sonnet-5-5@claude-code | m3: 400k total tokens, 20 min, $0.8 | fail | 51 | 148,854 | 18,167 | $0.1223 |  | medium (medium) | no |
| mypy-deferred-alias-crash | sol-6.1@codex | m4: 300k fresh tokens, 20 min, $1.2 | pass | 127 | 540,237 | 39,245 | $0.1596 |  | medium (medium) | no |
| mypy-deferred-alias-crash | opus-5-5@claude-code | m3: 400k total tokens, 20 min, $1.5 | pass | 174 | 256,185 | 35,651 | $0.4123 |  | medium (medium) | no |
| mypy-deferred-alias-crash | opus+haiku-swarm@claude-code | m3: 400k total tokens, 20 min, $1.5 | capped | 158 | 434,166 | 94,393 | $0.6219 | 13 | medium (medium) | yes: tokens 434166 > 400000 |
| mypy-deferred-alias-crash | sonnet-5-5@claude-code | m4: 300k fresh tokens, 20 min, $1.5 | fail | 43 | 131,266 | 17,605 | $0.1160 |  | medium (medium) | no |
| mypy-deferred-alias-crash | astra-6@codex | m3: 400k total tokens, 20 min, $2 | capped | 112 | 438,214 | 38,470 | $0.9088 |  | medium (medium) | yes: tokens 438214 > 400000 |
| mypy-deferred-alias-crash | opus+sonnet-team@claude-code | m3: 400k total tokens, 20 min, $2 | capped | 136 | 413,449 | 76,586 | $0.7135 | 3 | medium (medium) | yes: tokens 413449 > 400000 |
| mypy-deferred-alias-crash | opus-5-5@claude-code | m4: 300k fresh tokens, 20 min, $3 | pass | 265 | 626,464 | 53,215 | $0.6694 |  | medium (medium) | no |
| mypy-deferred-alias-crash | opus+haiku-swarm@claude-code | m4: 300k fresh tokens, 20 min, $3 | pass | 250 | 593,287 | 92,082 | $0.7139 | 10 | medium (medium) | no |
| removed-pilot-task | haiku-5-5@claude-code | m2: 250k total tokens, 10 min, $0.03 | pass | 27 | 88,138 | 19,492 | $0.0060 |  | medium (medium) | no |
| removed-pilot-task | haiku-5-5@claude-code | m2: 250k total tokens, 10 min, $0.03 | pass | 30 | 130,327 | 17,759 | $0.0061 |  | medium (medium) | no |
| removed-pilot-task | sol-6.1@codex | m2: 250k total tokens, 10 min, $0.3 | pass | 34 | 131,191 | 10,999 | $0.0440 |  | medium (medium) | no |
| removed-pilot-task | sol-6.1@codex | m2: 250k total tokens, 10 min, $0.3 | pass | 37 | 155,747 | 12,515 | $0.0482 |  | medium (medium) | no |
| removed-pilot-task | sonnet-5-5@claude-code | m2: 250k total tokens, 10 min, $0.4 | pass | 20 | 52,328 | 9,798 | $0.0585 |  | medium (medium) | no |
| removed-pilot-task | sonnet-5-5@claude-code | m2: 250k total tokens, 10 min, $0.4 | pass | 16 | 50,519 | 8,721 | $0.0530 |  | medium (medium) | no |
| removed-pilot-task | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | pass | 65 | 244,215 | 59,893 | $0.2809 | 10 | medium (medium) | no |
| removed-pilot-task | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | pass | 89 | 350,753 | 74,523 | $0.4122 | 10 | medium (medium) | no |
| removed-pilot-task | opus-5-5@claude-code | m2: 250k total tokens, 10 min, $0.75 | pass | 38 | 49,758 | 12,521 | $0.1448 |  | medium (medium) | no |
| removed-pilot-task | opus-5-5@claude-code | m2: 250k total tokens, 10 min, $0.75 | pass | 38 | 51,291 | 13,817 | $0.1575 |  | medium (medium) | no |
| removed-pilot-task | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 65 | 210,750 | 42,279 | $0.3440 | 3 | medium (medium) | no |
| removed-pilot-task | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 60 | 165,725 | 37,962 | $0.3124 | 3 | medium (medium) | no |
| removed-pilot-task | astra-6@codex | m2: 250k total tokens, 10 min, $1.5 | pass | 32 | 141,409 | 9,569 | $0.2659 |  | medium (medium) | no |
| removed-pilot-task | astra-6@codex | m2: 250k total tokens, 10 min, $1.5 | pass | 32 | 156,511 | 13,023 | $0.3137 |  | medium (medium) | no |
| taskiq-lazy-logging | haiku-5-5@claude-code | m2: 150k total tokens, 10 min, $0.03 | pass | 46 | 118,408 | 22,847 | $0.0075 |  | medium (medium) | no |
| taskiq-lazy-logging | haiku-5-5@claude-code | m2: 150k total tokens, 10 min, $0.03 | capped | 34 | 156,061 | 33,314 | $0.0101 |  | medium (medium) | yes: tokens 156061 > 150000 |
| taskiq-lazy-logging | sol-6.1@codex | m2: 150k total tokens, 10 min, $0.3 | capped | 53 | 151,989 | 23,733 | $0.0801 |  | medium (medium) | yes: tokens 151989 > 150000 |
| taskiq-lazy-logging | sol-6.1@codex | m2: 150k total tokens, 10 min, $0.3 | capped | 45 | 152,386 | 24,898 | $0.0796 |  | medium (medium) | yes: tokens 152386 > 150000 |
| taskiq-lazy-logging | sonnet-5-5@claude-code | m2: 150k total tokens, 10 min, $0.4 | pass | 48 | 90,567 | 20,276 | $0.1177 |  | medium (medium) | no |
| taskiq-lazy-logging | sonnet-5-5@claude-code | m2: 150k total tokens, 10 min, $0.4 | pass | 38 | 86,623 | 19,469 | $0.1141 |  | medium (medium) | no |
| taskiq-lazy-logging | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | capped | 65 | 412,298 | 106,617 | $0.3270 | 10 | medium (medium) | yes: tokens 412298 > 400000 |
| taskiq-lazy-logging | opus+haiku-swarm@claude-code | m2: 400k total tokens, 15 min, $0.7 | capped | 69 | 409,882 | 106,044 | $0.4225 | 10 | medium (medium) | yes: tokens 409882 > 400000 |
| taskiq-lazy-logging | opus-5-5@claude-code | m2: 150k total tokens, 10 min, $0.75 | pass | 78 | 148,929 | 30,582 | $0.3403 |  | medium (medium) | no |
| taskiq-lazy-logging | opus-5-5@claude-code | m2: 150k total tokens, 10 min, $0.75 | capped | 64 | 166,361 | 33,578 | $0.3589 |  | medium (medium) | yes: tokens 166361 > 150000 |
| taskiq-lazy-logging | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 91 | 379,644 | 66,146 | $0.5554 | 3 | medium (medium) | no |
| taskiq-lazy-logging | opus+sonnet-team@claude-code | m2: 400k total tokens, 15 min, $1.3 | pass | 77 | 356,085 | 57,320 | $0.4885 | 3 | medium (medium) | no |
| taskiq-lazy-logging | astra-6@codex | m2: 150k total tokens, 10 min, $1.5 | capped | 49 | 161,277 | 25,341 | $0.4815 |  | medium (medium) | yes: tokens 161277 > 150000 |
| taskiq-lazy-logging | astra-6@codex | m2: 150k total tokens, 10 min, $1.5 | capped | 51 | 152,911 | 34,255 | $0.5629 |  | medium (medium) | yes: tokens 152911 > 150000 |
| werkzeug-apply-conditions | haiku-5-5@claude-code | m3: 400k total tokens, 20 min, $0.1 | capped | 98 | 435,107 | 78,175 | $0.0261 |  | medium (medium) | yes: tokens 435107 > 400000 |
| werkzeug-apply-conditions | haiku-5-5@claude-code | m4: 300k fresh tokens, 20 min, $0.3 | fail | 268 | 2,131,566 | 149,430 | $0.0664 |  | medium (medium) | no |
| werkzeug-apply-conditions | sol-6.1@codex | m3: 400k total tokens, 20 min, $0.6 | capped | 413 | 441,246 | 60,702 | $0.2447 |  | medium (medium) | yes: tokens 441246 > 400000 |
| werkzeug-apply-conditions | sonnet-5-5@claude-code | m3: 400k total tokens, 20 min, $0.8 | capped | 120 | 433,272 | 63,030 | $0.4263 |  | medium (medium) | yes: tokens 433272 > 400000 |
| werkzeug-apply-conditions | sol-6.1@codex | m4: 300k fresh tokens, 20 min, $1.2 | pass | 302 | 1,247,098 | 84,346 | $0.3913 |  | medium (medium) | no |
| werkzeug-apply-conditions | opus-5-5@claude-code | m3: 400k total tokens, 20 min, $1.5 | capped | 185 | 405,391 | 77,582 | $0.9397 |  | medium (medium) | yes: tokens 405391 > 400000 |
| werkzeug-apply-conditions | opus+haiku-swarm@claude-code | m3: 400k total tokens, 20 min, $1.5 | capped | 128 | 401,913 | 91,394 | $0.3492 | 6 | medium (medium) | yes: tokens 401327 > 400000 |
| werkzeug-apply-conditions | sonnet-5-5@claude-code | m4: 300k fresh tokens, 20 min, $1.5 | pass | 61 | 171,454 | 35,434 | $0.2213 |  | medium (medium) | no |
| werkzeug-apply-conditions | opus+sonnet-team@claude-code | m4: 300k fresh tokens, 20 min, $1.6385 | pass | 237 | 998,512 | 155,377 | $1.2842 | 4 | medium (medium) | no |
| werkzeug-apply-conditions | astra-6@codex | m3: 400k total tokens, 20 min, $2 | capped | 215 | 452,646 | 56,614 | $1.3230 |  | medium (medium) | yes: tokens 452646 > 400000 |
| werkzeug-apply-conditions | opus+sonnet-team@claude-code | m3: 400k total tokens, 20 min, $2 | capped | 179 | 406,471 | 97,543 | $0.8464 | 4 | medium (medium) | yes: tokens 406394 > 400000 |
| werkzeug-apply-conditions | opus-5-5@claude-code | m4: 300k fresh tokens, 20 min, $3 | pass | 278 | 705,875 | 102,425 | $1.2756 |  | medium (medium) | no |
| werkzeug-apply-conditions | opus+haiku-swarm@claude-code | m4: 300k fresh tokens, 20 min, $3 | capped | 209 | 1,400,130 | 302,140 | $0.9999 | 11 | medium (medium) | yes: fresh tokens 302087 > 300000 |

Total $27.1043 dollar-equivalent over 81 run(s); prices 2026-10-09. Subscription runs: not billed per token, but they use plan limits.
