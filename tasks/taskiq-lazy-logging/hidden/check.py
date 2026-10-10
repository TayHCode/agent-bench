"""Hidden check for taskiq-lazy-logging. Runs from the working copy after the agent is done.

1. ruff's flake8-logging-format rules (G) report nothing under taskiq/
2. pyproject.toml enables the "G" rule family for ruff
3. every log message that was an f-string before still exists in the same file (same text, same
   number of placeholders), so the change did not reword or drop messages
4. the original test-suite (pristine copy) still passes
"""
import ast
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = Path.cwd()
LEVELS = {"debug", "info", "warning", "warn", "error", "exception", "critical", "fatal", "log"}
ok = True


def step(name, passed, detail=""):
    global ok
    ok = ok and passed
    print(f"[{'PASS' if passed else 'FAIL'}] {name}")
    if detail and not passed:
        print(detail[-1500:])


def run(cmd):
    r = subprocess.run(cmd, cwd=WORK, capture_output=True, text=True, timeout=600)
    return r.returncode == 0, r.stdout + r.stderr


def norm(text):
    text = re.sub(r"%\(\w+\)[sdrif]|%[sdrif]", "%", text)
    return " ".join(text.split())


def templates(path):
    out = []
    try:
        tree = ast.parse(Path(path).read_text())
    except SyntaxError:
        return None
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in LEVELS and n.args:
            a = n.args[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                out.append(norm(a.value))
            elif isinstance(a, ast.JoinedStr):
                out.append(norm("".join(p.value if isinstance(p, ast.Constant) else "%" for p in a.values)))
    return out


ok_ruff, out = run(["uv", "run", "--no-project", "--with", "ruff", "ruff", "check", "--select", "G",
                    "--isolated", "--no-cache", "taskiq"])
step("ruff G (logging format) clean", ok_ruff, out)

cfg = tomllib.loads((WORK / "pyproject.toml").read_text())
select = cfg.get("tool", {}).get("ruff", {}).get("lint", {}).get("select", [])
select = select or cfg.get("tool", {}).get("ruff", {}).get("select", [])
step('pyproject ruff select contains "G"', "G" in select or any(s.startswith("G") for s in select), f"select={select}")

expected = json.loads((HERE / "expected_messages.json").read_text())
missing = []
for rel, msgs in expected.items():
    have = templates(WORK / rel)
    if have is None:
        missing.append((rel, "unparseable"))
        continue
    pool = list(have)
    for m in msgs:
        if m in pool:
            pool.remove(m)
        else:
            missing.append((rel, m))
step("existing log messages preserved", not missing, "\n".join(f"{r}: {m}" for r, m in missing))

ok_t, out = run(["uv", "run", "--no-project", "--with-editable", ".", "--with", "tzdata", "--with", "pytest",
                 "--with", "pytest-asyncio", "--with", "freezegun", "--with", "poly" + "fac" + "tory", "--with", "pytest-xdist",
                 "--with", "pytest-mock", "--with", "cbor2", "--with", "msgpack", "--with", "orjson",
                 "--with", "prometheus_client", "--with", "watchdog", "--with", "gitignore-parser",
                 "python", "-m", "pytest", str(HERE / "tests"), "--ignore", str(HERE / "tests" / "opentelemetry"),
                 "-q", "-p", "no:cacheprovider", "-n", "0", "--rootdir", str(WORK), "-c", "pyproject.toml"])
step("original test-suite passes", ok_t, out)
sys.exit(0 if ok else 1)
