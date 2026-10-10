"""Run the README's no-login walkthrough in a new ignored temporary directory."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from toyrepo import make_toy

root = Path(__file__).resolve().parents[1]
base = root / ".fresh-user"
base.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="demo-", dir=base) as name:
    demo = Path(name)
    env = os.environ | {"AGENTBENCH_HOME": str(demo / "home"), "AGENTBENCH_CACHE": str(demo / "cache")}
    sha = make_toy(demo / "toy")

    def command(*args):
        subprocess.run([sys.executable, "-m", "agentbench.cli", *args], check=True, cwd=demo, env=env)

    command("--help")
    command("task", "from-commit", str(demo / "toy"), sha, "--id", "toy-null-total",
            "--check", "python3 -m unittest discover -s tests")
    task = demo / "home/tasks/toy-null-total"
    (task / "prompt.md").write_text("Fix total(None) so it returns zero.\n")
    command("plan", "--ledger-cap", "1")
    stub = demo / "claude-stub"
    shutil.copyfile(root / "tests/stub_claude.py", stub)
    stub.chmod(0o700)
    stub.with_name(stub.name + ".json").write_text(json.dumps({"fix_dir": str(task / "gold")}))
    env["AGENTBENCH_CLAUDE_BIN"] = str(stub)
    command("run", "--task", "toy-null-total", "--contestant", "haiku-5-5@claude-code",
            "--profile", "byo", "--out", "runs")
    record = json.loads(next((demo / "runs").glob("*/run.json")).read_text())
    assert record["status"] == "ok" and record["passed"] and not record.get("peeked")
    command("report", "--runs", "runs", "--html", "results.html")
    assert (demo / "results.html").stat().st_size > 0
print("README demo passed; temporary files removed.")
