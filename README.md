# agent-bench

**Privacy first.** The runner has no telemetry, update check or upload. Installation and preparation may download public dependencies or task inputs. Real agents send code they read to their vendors; an optional judge sends the prompt and diff to its selected provider. Review private tasks before running them. A clean HOME is not a sandbox: hidden tests are not container-isolated.

Compare coding agents on work you can check: pass/fail, time, tokens and dollar-equivalent cost. Turn a past bug fix into a task with hidden regression tests and run contestants on fresh checkouts. Deterministic checks decide pass/fail; no model decides gate passage.

## Quickstart: three commands, no login, no cost

Run these from the downloaded checkout. Needs Python 3.11+ and Git. Tested on macOS, Linux and WSL; on native Windows use WSL (`wsl --install`).

```sh
python -m pip install .
agentbench doctor
agentbench demo
```

Use a virtual environment first if your system Python refuses installs:

```sh
python3 -m venv .venv
. .venv/bin/activate
```

If `venv` is missing, `uv venv --python 3.12 .venv` creates it; after activation,
use `uv pip install .` in place of the install command. macOS's built-in Python
may be too old: use `uv` or `brew install python@3.12`. Without installing the
package, Python 3.11+ can run `PYTHONPATH=src python3 -m agentbench demo` from a
checkout. `uvx --from . agentbench demo` also works from a checkout.

Then compare real agents on your own code:

```sh
agentbench start        # asks three questions, checks your setup, shows the cost, asks yes/no, runs, prints the table
agentbench demo --real  # optional first: one real run of the cheapest logged-in agent on the toy task, capped at $0.05 (asks first)
```

`demo` builds a toy repo, hides the test that proves a bug fixed, and runs two built-in stand-in agents: one copies the known fix, one does nothing. They cost nothing and use no model, so they test the plumbing, not any agent. `start` needs `claude` or `codex` installed and logged in; `doctor` tells you exactly what to run if not.

### What you should see (abridged; your numbers will differ)

```text
$ agentbench doctor
agentbench doctor (Linux, Python 3.12.3)
  ok      platform: Linux
  ok      python: Python 3.12.3
  ok      git: git version 2.43.0
  ok      disk: 114 GB free
  ok      claude: claude 2.1.296 (Claude Code): logged in (claude.ai)
  note    codex: codex is not installed
          fix: npm install -g @openai/codex
Ready. Real runs are possible with: claude-code. Try `agentbench demo`, then `agentbench start`.

$ agentbench demo
1/3  Building a toy task: a small repo, a bug, and a hidden test that proves it is fixed ...
2/3  Running two free stand-in agents on it (no model, no network, $0) ...
3/3  Results:

Contestant   Result  Time  Tokens  $ equiv
-----------  ------  ----  ------  -------
stub-solver  pass    0.0s   1,060  $0.0000
stub-lazy    FAIL    0.0s   1,060  $0.0000

Full report: results.html
stub-solver copies the known fix and stub-lazy changes nothing: they test the pipeline, not any model. Run `agentbench start` to compare real agents on your own code.
Next: agentbench doctor, then agentbench start

$ agentbench start
agentbench start: compare coding agents on a bug your repo already fixed.
1/3  Which repository? (path to a git repo) [.] ~/code/myapp
  1) 3483b75f  total() crashes on an empty cart
  2) 9c1e04aa  Fix off-by-one in pagination
2/3  Which past fix? Number, commit SHA, or w to write your own task [1] 1
3/3  Which agents to compare? (comma list, or 'stub' for free stand-ins) [haiku-5-5@claude-code,sonnet-5-5@claude-code]
... doctor report ...
Building a task from 3483b75f (the bug's start state, a hidden test, and a check that proves the fix) ...
verified: unfixed fails, fixed passes, both twice; the check takes 1.2 s

Plan: 1 task(s) x 2 contestant(s) x 1 repeat(s) = 2 runs, one at a time
  haiku-5-5@claude-code: claude-code / claude-haiku-5-5, up to $1, 10 min, 100,000 fresh tokens per run; expected $0.006 a run
  sonnet-5-5@claude-code: claude-code / claude-sonnet-5-5, up to $1, 10 min, 100,000 fresh tokens per run; expected $0.116 a run
  ledger cap    $1.00: the matrix stops once recorded spend is within 10% of it ($0.90)
Cheapest first: haiku-5-5@claude-code runs first; the others (sonnet-5-5@claude-code) are skipped on a task only if that task proves broken.
Go ahead? [y/N] y
...
Contestant              Result  Time    Tokens  $ equiv
----------------------  ------  -----  -------  -------
(one row per agent: pass or FAIL, time, tokens, dollar-equivalent)
Full report: results.html
Same run without questions: agentbench start --repo ~/code/myapp --commit 3483b75f0724 --agents haiku-5-5@claude-code,sonnet-5-5@claude-code --ledger-cap 1 --yes
```

Every question has a flag, so scripts and CI never wait for input: `agentbench start --repo ./myapp --commit FIX_SHA --agents haiku-5-5@claude-code,sonnet-5-5@claude-code --ledger-cap 1 --yes`. Other flags: `--task NAME` (a task you already built), `--prompt 'what is wrong'`, `--check`/`--setup` (when the test command guess is wrong), `--repeats N`, `--html FILE`, `--no-open`. `agentbench start --agents stub` rehearses your own repo for free.

**Cheapest first.** `start` and `matrix` run the cheapest contestant first on each task. Pricier contestants are skipped on a task only when the cheapest one did not pass and the task proves broken (its check fails on the known fix, or passes without any fix); otherwise everyone runs. Spending stops at the ledger cap. `--repeats N` runs each contestant N times per task.

**When something fails** you get what happened and one command to fix it, never a stack trace:

```text
error: ./notes is not a git repository
fix:   cd into your project (or pass --repo PATH) and run `agentbench start` again
```

Add `--debug` to any command for the full trace.

## Bring your own tasks

For real runs, install and log in to `claude` or `codex` separately. Select a commit in a repository you own that fixes a bug and adds or changes a test:

```sh
agentbench task from-commit ./myapp FIX_COMMIT --id myapp-null-total
```

Replace the placeholders. Tasks go in `~/.agentbench/tasks/`, or `AGENTBENCH_HOME/tasks` when set. Rewrite the generated `prompt.md` to state the problem without revealing the fix, and delete its DRAFT marker. `from-commit` uses the commit's parent, discards history and remotes, hides changed tests, and retains other changed files as gold. It proves twice that the unfixed tree fails and twice that the fixed tree passes. Override guessed commands with `--check 'COMMAND'` and `--setup 'COMMAND'`; merge commits need `--base`. Common secret files are removed and recognized secret-shaped strings rejected. This scan is incomplete: review the task yourself.

```sh
agentbench plan --ledger-cap 1
agentbench matrix --ledger-cap 1
agentbench report --runs ~/.agentbench/runs --html results.html
```

Defaults: first three user tasks, first two contestants, one repeat, sequential runs; per run, 100,000 fresh tokens, $1 equivalent and ten minutes. The ledger is a dollar-equivalent budget even on subscriptions; plans above $2 require confirmation. Reports exclude peeked runs. Add `--repeats 2` or more to explore variability; one run does not establish reliability.

### Free from-commit rehearsal

After installing, make a new working directory (for example `.fresh-user/rehearsal`
inside this checkout) and run the following there. No model login is needed.
`doctor` can report missing real-agent logins while the free demo still works.

```sh
export AGENTBENCH_HOME="$PWD/bench-home"
python -m agentbench.toy toy
FIX_COMMIT=$(git -C toy rev-parse HEAD)
agentbench task from-commit ./toy "$FIX_COMMIT" --id toy-null-total --check 'python3 -m unittest discover -s tests'
python -c "from pathlib import Path; Path('bench-home/tasks/toy-null-total/prompt.md').write_text('Fix total(None) so it returns zero.\n')"
agentbench plan --tasks toy-null-total --contestants stub-solver --ledger-cap 1
agentbench run --task toy-null-total --contestant stub-solver --profile byo --out runs
```

The builder verifies start and gold twice. The last command should report
`passed=True` and $0; the stand-in copies gold, so this checks the pipeline only.

## Contestants

Use `~/.agentbench/contestants.toml` or `--contestants-file`. The first two entries are the default pair. Built-in model names and prices reflect the dated experiments, not a promise of current availability. Choose names available to your CLI and review prices before spending.

```toml
[contestants.cheap]
cli = "claude-code"
model = "claude-haiku-5-5"
effort = "medium"

[contestants.strong]
cli = "codex"
model = "gpt-6.1-sol"
effort = "medium"
max_usd = 0.5

[prices."your-model"]
input = 1.0
output = 5.0
cache_read = 0.1
cache_write = 1.0
```

Each run has a clean HOME; login files are linked, never copied. Optional `files` entries copy explicitly selected rule files. Directories, credentials and implicit paths outside the user's home are refused; explicit mappings can select other locations. The runner constructs each CLI's canonical config locations at runtime. On macOS a Keychain-only Claude subscription login may not work through a clean HOME: use an API key or Linux/WSL. Real macOS subscription runs have not been verified.

## Built-in tasks

Nine task definitions ship in `tasks/`, each with a prompt, deterministic check,
manifest and LICENSE-SOURCE. Two data tasks include inputs and known answers;
QCEW downloads checksum-pinned archives and constructs answers at preparation.
The six code tasks download pinned base and fix commits instead of vendoring
upstream trees. Sources and full licence notices are in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

| Task | Public source | Licence |
| --- | --- | --- |
| humanize-intcomma-overflow | [humanize #392](https://github.com/python-humanize/humanize/pull/392) | MIT |
| taskiq-lazy-logging | [taskiq #665](https://github.com/taskiq-python/taskiq/pull/665) | MIT |
| mypy-deferred-alias-crash | [mypy #22096](https://github.com/python/mypy/pull/22096) | MIT; typeshed notices retained |
| werkzeug-apply-conditions | [Werkzeug #3308](https://github.com/pallets/werkzeug/pull/3308) | BSD-3-Clause |
| fda-recalls-clean | [openFDA enforcement](https://open.fda.gov/data/food/enforcement/) | CC0 / public domain |
| irs-donee-matching | [IRS registry](https://www.irs.gov/charities-non-profits/exempt-organizations-business-master-file-extract-eo-bmf) | US government public domain |
| pydantic-namespace-inspection | [Pydantic #13596](https://github.com/pydantic/pydantic/pull/13596) | MIT; core notice retained |
| mypy-paramspec-unpack-crash | [mypy #22123](https://github.com/python/mypy/pull/22123) | MIT; typeshed notices retained |
| qcew-county-shift-share | [BLS QCEW](https://www.bls.gov/cew/downloadable-data-files.htm) | US government public domain |

The code-task PR authors and commit messages were reviewed for AI authorship markers; none were found. Undisclosed AI use cannot be ruled out. Data answers are generated deterministically by `build_reference.py`, not written by a model. Synthetic fixtures under `tests/` test the runner and are excluded from the benchmark pool.

One pilot task from a third-party library was removed to keep the licence trail clean. Its historical results remain labelled `removed-pilot-task`; this tree cannot rerun it. Code snapshots and their upstream contact metadata are downloaded only after explicit preparation. Source and gold come from the pinned human-authored upstream commits, not generated code. The released data copies generalize public entity labels that overlap private terms; record IDs, dates, values and check rules remain. Dependencies are not locked, so future results may differ.

Prepare a code task first (requires GitHub access), then verify it before a real run:

```sh
agentbench task prepare mypy-deferred-alias-crash --tasks-dir .fresh-user/prepared
agentbench verify --task mypy-deferred-alias-crash --tasks-dir .fresh-user/prepared --scratch .fresh-user/verify-mypy
```

This example writes to the ignored `.fresh-user/prepared` directory and refuses to overwrite a task. Without `--tasks-dir`, preparation writes to your user task directory. Repeat with another code-task ID; use `--tasks-dir` consistently on prepare, verify and run. Preparation resolves both downloaded commits and checks their full hashes against the pinned recipe before extracting source, gold and tests. It makes Git network requests; model runs still have no telemetry from this runner.

QCEW uses the same command, with an optional download-cache override:

```sh
agentbench task prepare qcew-county-shift-share --tasks-dir .fresh-user/prepared --cache-dir .fresh-user/downloads
agentbench verify --task qcew-county-shift-share --tasks-dir .fresh-user/prepared --scratch .fresh-user/verify-qcew
```

It downloads about 356 MB (about 2.67 GB of CSV inside the ZIPs), checks SHA-256
before creating a task, and keeps inputs only in the visible `repo/data/`.
Known answers stay in `gold/` and `hidden/`. Inputs and answer construction cost
no model tokens; leave enough disk space for preparation and fresh checkouts.
Prepared user tasks are selected automatically unless `--tasks-dir` is supplied.

Code-task checks need `uv`; mypy and Werkzeug request Python 3.13 through `uv`. They install dependencies and run one suite at a time. Verification spends no model tokens:

```sh
agentbench verify --task fda-recalls-clean --scratch .fresh-user/verify-fda
```

For a real run, check the plan and CLI login first:

```sh
agentbench plan --task fda-recalls-clean --contestants haiku-5-5@claude-code --ledger-cap 1
agentbench matrix --task fda-recalls-clean --contestants haiku-5-5@claude-code --ledger-cap 1
```

Profiles: M2 uses the pilot's per-contestant caps; M3 caps total tokens at 400k including cache reads; M4 caps fresh tokens at 300k; `byo` uses the smaller defaults above. `--task` alone selects the older M2 profile and all contestants: name contestants explicitly for one cheap run.

## Optional judge

A second, secondary score: an LLM judge that is not one of the contestants' labs rates each run's change from 1 to 5 on four items (correct approach, minimal and clean, no unrelated edits, follows the prompt). **Pass/fail from the hidden check stays the primary result; a judge never decides it**, never sees the hidden tests or the real fix, and can be wrong. Its score goes in a per-run `judge.json` (scores, one-line reason, judge model, prompt hash, cost); `run.json` is untouched. The report adds a "Quality (judge, secondary)" column and a footnote naming the judge only if a judge ran.

```
agentbench judge --runs runs --judge gemini --dry-run          # estimate, sends nothing
agentbench judge --runs runs --judge gemini --max-usd 1        # hard cap; a paid judge refuses to run without it
agentbench judge --runs runs --judge "my-judge --json"         # any command: packet (JSON) on stdin, verdict JSON on stdout
agentbench judge --runs runs --judge gemini --max-usd 1 --agree 5   # re-judge 5 runs with another seed, report disagreement
```

`judge.toml` (in the current folder or `~/.agentbench/`, or `--judge-file`) configures the backends: `[gemini]` (`model = "gemini-2.5-pro"`, `api_key_env = "GEMINI_API_KEY"`, `price_in`/`price_out` in USD per million tokens, `max_output_tokens`), `[command]` (`cmd`, optional `usd_per_call`), `default = "gemini"`. `--judge stub` is a free fake for tests. The verdict a command must print is `{"scores": {"approach": 4, "minimal": 5, "no_unrelated": 5, "follows_prompt": 4}, "reason": "one line"}`.

- **Blind.** The packet holds the task prompt, the diff the contestant produced and the rubric. Contestant, model and CLI names are removed, runs get ids like `sample-3`, and order and rubric order are shuffled with a fixed seed (`--seed`). Names are removed by exact match only: a diff that mentions its own author gives it away.
- **Privacy.** `--judge gemini` sends the task prompt and the diff to the Google API; a command judge sends them wherever your command does. Nothing is sent unless you pick a judge, and `--dry-run` shows what would go. The backend reads authentication from the environment variable without storing it. The Gemini call lives in its own module, the only one that touches the network.
- **Cost.** The estimate before any call assumes 3 characters per input token and the full `max_output_tokens` as output (thinking tokens are billed as output); the real cost comes from the API's token counts. Before each call the judge stops if the call could pass `--max-usd`, so unjudged runs are a random subset (the order is shuffled), not one contestant's. Check the current price before relying on `price_in`/`price_out`.
- **Agreement.** `--agree N` judges N sampled runs a second time with another seed and writes `judge-agreement.json` (exact item agreement, mean difference, runs off by 2+). Treat a judge that disagrees with itself as noise.
- Runs that already have a `judge.json` are skipped unless `--force`. Runs with no kept `work/` checkout, no diff, or a task that is not available are skipped.

## Published measurements

Read [the pilot](evidence/m2-pilot-results.md), [M3](evidence/m3-results.md), [M4](evidence/m4-results.md), their conclusions and local HTML counterparts. [results.csv](evidence/results.csv) contains the compact per-run table from the final report, preserving rounded values and cap profiles. Raw run JSON and transcripts are omitted because they can contain paths, session IDs and output. The CSV cannot reconstruct per-file diffs or independently recompute every table.

These exploratory experiments use short tasks and do not rank models: pilot cells have one or two repeats; M3/M4 cells have n=1. Total-token caps dominated M3. M4 is incomplete: both Astra hard-task cells and the Sonnet-team mypy cell are missing. Haiku/Sonnet probes influenced task selection. Costs are dated list-price equivalents of subscription usage, not invoices. Keep cap profiles separate and distinguish capped work passing checks from completed passes. The [cost plan](evidence/cost-plan.md) is historical; the [price table](evidence/price-table.md) records its assumptions.

## Safety and limitations

Agents send code they read to their vendors. Review private tasks before selecting contestants. A clean HOME and disposable checkout are not a sandbox: agents run as your OS user and may reach hidden tests or other files. MCP/connectors are disabled in supported CLI invocations, but filesystem and network access remain. Peek detection catches obvious commands naming hidden/gold paths, fix commits or source URLs; it is incomplete. Task setup and checks execute task-provided code. Use trusted code and isolation when needed.

Data records are benchmark text, not medical, tax or eligibility guidance. Neither agencies nor upstream maintainers endorse this project. Prices, CLI event formats and dependencies may drift. Only `agentbench demo` and deterministic checks are needed to try the runner without a login; the stand-in agents say nothing about any model.

## Development

```sh
python -m unittest discover -s tests -q
```

`sh tests/install_check.sh` installs into a fresh environment and runs `doctor` and `demo` (and `uvx` if present); `python tests/readme_demo.py` runs the older step-by-step stub walkthrough. The suite includes a full shipping-tree privacy regression check and synthetic scanner fixtures. Run one suite process at a time. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md). Runner license: MIT, copyright TayHCode.
