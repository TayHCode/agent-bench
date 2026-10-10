"""Task folders: task.toml, prompt, repo/ (visible), hidden/ (checks, copied in after the run)."""

import os
import shlex
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path

_PACKAGED_TASKS = Path(__file__).resolve().parent / "builtin_tasks"
DEFAULT_TASKS = _PACKAGED_TASKS if _PACKAGED_TASKS.is_dir() else Path(__file__).resolve().parents[2] / "tasks"


def agentbench_home():
    """Where a person's own tasks, runs and contestants live: $AGENTBENCH_HOME, else ~/.agentbench."""
    return Path(os.environ.get("AGENTBENCH_HOME") or Path.home() / ".agentbench")


def user_tasks_dir():
    return agentbench_home() / "tasks"


def find_task_root(task_id, tasks_dir=None):
    """An explicit tasks dir wins; otherwise the built-in tasks, then the person's own (~/.agentbench/tasks)."""
    if tasks_dir:
        return Path(tasks_dir) / task_id
    for base in (DEFAULT_TASKS, user_tasks_dir()):
        if (base / task_id / "task.toml").exists():
            if any((base / task_id / name).exists() for name in ("snapshot.toml", "data_recipe.toml")) and (user_tasks_dir() / task_id / "repo").is_dir():
                return user_tasks_dir() / task_id
            return base / task_id
    return DEFAULT_TASKS / task_id


def load_task(task_id, tasks_dir=None):
    root = find_task_root(task_id, tasks_dir)
    if (root / "snapshot.toml").exists() or ((root / "data_recipe.toml").exists() and not (root / "repo").is_dir()):
        raise ValueError(f"prepare this built-in task first: agentbench task prepare {task_id}")
    meta = tomllib.loads((root / "task.toml").read_text())
    meta["root"] = root
    meta["prompt_text"] = (root / meta["prompt"]).read_text()
    return meta


def prepare_workdir(task, workdir):
    """Fresh single-commit checkout of repo/ with no history from anywhere else."""
    shutil.copytree(task["root"] / "repo", workdir)
    env = {"GIT_AUTHOR_NAME": "bench", "GIT_AUTHOR_EMAIL": "benchmark",
           "GIT_COMMITTER_NAME": "bench", "GIT_COMMITTER_EMAIL": "benchmark"}
    cmds = [["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-q", "-m", "start"]]
    if task.get("git_tag"):  # some builds (versioningit) need one tag to find a version
        cmds.append(["tag", task["git_tag"]])
    for cmd in cmds:
        subprocess.run(["git", "-C", str(workdir), *cmd], check=True, env=env | _base_env())


def _base_env():
    import os
    return {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "LANG")}


def resolve_check(cmd):
    """`agentbench ...` in a check always means this install, whether or not the console script is on PATH."""
    if cmd and cmd[0] == "agentbench":
        return [sys.executable, "-m", "agentbench.cli", *cmd[1:]]
    return list(cmd)


def run_check(task, workdir, timeout=None):
    """Copy the hidden tests in after the run and execute the check command.

    hidden/ becomes tests_hidden/. hidden/overlay/ (tests from a from-commit task) is instead copied over the
    working tree at its own paths, replacing whatever the agent left there, so the project's own test runner finds it.
    """
    hidden = Path(workdir) / "tests_hidden"
    shutil.rmtree(hidden, ignore_errors=True)
    try:
        shutil.copytree(task["root"] / "hidden", hidden, ignore=shutil.ignore_patterns("overlay"))
        overlay = task["root"] / "hidden" / "overlay"
        if overlay.is_dir():
            shutil.copytree(overlay, workdir, dirs_exist_ok=True)
    except (OSError, shutil.Error) as e:
        return False, f"could not copy the hidden tests in: {e}"
    timeout = timeout or task.get("check_timeout", 60)
    env = os.environ | {"PYTHONPATH": os.pathsep.join(filter(None, [str(Path(__file__).resolve().parents[1]), os.environ.get("PYTHONPATH")]))}
    try:
        r = subprocess.run(resolve_check(task["check"]), cwd=workdir, capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return False, "check timed out"
    except OSError as e:
        return False, f"check could not start: {e}"
    return r.returncode == 0, (r.stdout + r.stderr)[-2000:]


def run_setup(task, workdir, env=None):
    """Run the task's `setup` command (install dependencies) in the checkout, before the agent starts.

    Not billed: it runs outside the contestant's meter and clock. Whatever it creates becomes part of the start
    state, so the agent's diff counts only its own changes. Returns (ok, output tail, seconds).
    """
    cmd = task.get("setup")
    if not cmd:
        return True, "", 0.0
    argv = shlex.split(cmd) if isinstance(cmd, str) else list(cmd)
    t0 = time.monotonic()
    try:
        r = subprocess.run(argv, cwd=workdir, capture_output=True, text=True, env=env, timeout=task.get("setup_timeout", 600))
        ok, out = r.returncode == 0, (r.stdout + r.stderr)[-1500:]
    except subprocess.TimeoutExpired:
        ok, out = False, "setup timed out"
    except OSError as e:
        ok, out = False, f"setup could not start: {e}"
    if ok:
        _fold_setup_into_start(workdir)
    return ok, out, time.monotonic() - t0


def _fold_setup_into_start(workdir):
    """New top-level files/dirs the setup made are ignored; edits it made to tracked files are folded into the start commit."""
    git = ["git", "-C", str(workdir)]
    status = subprocess.run([*git, "status", "--porcelain", "--untracked-files=normal", "-z"], capture_output=True, text=True).stdout
    untracked = [e[3:] for e in status.split("\0") if e.startswith("?? ")]
    if untracked:
        with open(Path(workdir) / ".git" / "info" / "exclude", "a") as f:
            f.write("".join(f"/{u}\n" for u in untracked))
    if any(e and not e.startswith("?? ") for e in status.split("\0")):
        env = _base_env() | {"GIT_AUTHOR_NAME": "bench", "GIT_AUTHOR_EMAIL": "benchmark",
                             "GIT_COMMITTER_NAME": "bench", "GIT_COMMITTER_EMAIL": "benchmark"}
        subprocess.run([*git, "add", "-u"], capture_output=True, env=env)
        subprocess.run([*git, "commit", "-q", "--amend", "--no-edit"], capture_output=True, env=env)


def diff_summary(workdir, stage=True):
    """Totals and per-file lines changed against the start commit (stage=False reads an already-staged checkout)."""
    if stage:
        subprocess.run(["git", "-C", str(workdir), "add", "-A"], capture_output=True)
    r = subprocess.run(["git", "-C", str(workdir), "diff", "--numstat", "HEAD", "--", ".", ":(exclude)**/__pycache__/**",
                        ":(exclude)tests_hidden"], capture_output=True, text=True)
    rows = [l.split("\t") for l in r.stdout.splitlines() if l.strip()]
    files = [{"path": p, "added": int(a) if a.isdigit() else 0, "removed": int(d) if d.isdigit() else 0} for a, d, p in rows]
    return {"files_changed": len(files), "lines_added": sum(f["added"] for f in files),
            "lines_removed": sum(f["removed"] for f in files), "files": files}


def is_test_path(path):
    parts = path.split("/")
    name = parts[-1]
    return (any(p in ("tests", "test", "tests_hidden", "__tests__", "test-data") for p in parts[:-1]) or name.startswith("test_")
            or ".test." in name or ".spec." in name or name.endswith(".test"))


def is_doc_path(path):
    """Docs and change logs: part of a real fix, but not source lines."""
    parts = path.split("/")
    name = parts[-1].lower()
    return (parts[0] in ("docs", "doc") or name in ("changes.rst", "changes.md", "changelog.md", "changelog.rst", "news", "history.md")
            or "changelog" in parts[:-1])


def is_generated_path(path):
    """Lockfiles an install writes; not part of a change a person would review."""
    return path.rsplit("/", 1)[-1] in ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "uv.lock", "poetry.lock", "Cargo.lock")


def gold_diff(task):
    """Lines the real upstream fix changed in the start checkout, per file (gold/ holds only the changed files)."""
    import difflib
    files = []
    gold = task["root"] / "gold"
    for g in sorted(p for p in gold.rglob("*") if p.is_file()):
        rel = g.relative_to(gold).as_posix()
        start = task["root"] / "repo" / rel
        old = start.read_text().splitlines() if start.exists() else []
        new = g.read_text().splitlines()
        added = removed = 0
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
            if tag != "equal":
                removed += i2 - i1
                added += j2 - j1
        files.append({"path": rel, "added": added, "removed": removed})
    return files


def apply_gold(task, workdir):
    """Overlay the real upstream fix (task gold/ files) onto a working copy."""
    shutil.copytree(task["root"] / "gold", workdir, dirs_exist_ok=True)
    for rel in task.get("gold_delete", []):  # files the real fix removed
        (Path(workdir) / rel).unlink(missing_ok=True)


def verify_task(task, scratch, repeats=1):
    """Prove a task is usable: the unfixed start fails the check, the real fix passes it.

    With repeats > 1 each side is checked that many times; a side whose runs disagree is flaky and the task is rejected.
    """
    scratch = Path(scratch)
    shutil.rmtree(scratch, ignore_errors=True)
    out = {"task": task["id"], "setup_failed": False, "check_seconds": 0.0}
    sides = {}
    for name in ("start", "fixed"):
        work = scratch / name
        prepare_workdir(task, work)
        if name == "fixed":
            apply_gold(task, work)
        ok, setup_out, _ = run_setup(task, work)
        if not ok:
            return out | {"setup_failed": True, "setup_output_tail": setup_out, "start_fails": False, "gold_passes": False,
                          "flaky": False, "start_output_tail": "", "gold_output_tail": ""}
        results = []
        for _ in range(repeats):
            t0 = time.monotonic()
            results.append(run_check(task, work))
            out["check_seconds"] = max(out["check_seconds"], time.monotonic() - t0)
        sides[name] = results
    start, fixed = [r[0] for r in sides["start"]], [r[0] for r in sides["fixed"]]
    return out | {"start_fails": not any(start), "gold_passes": all(fixed),
                  "flaky": len(set(start)) > 1 or len(set(fixed)) > 1,
                  "start_output_tail": sides["start"][-1][1][-600:], "gold_output_tail": sides["fixed"][-1][1][-600:]}
