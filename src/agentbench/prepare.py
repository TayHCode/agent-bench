"""Reconstruct bundled code tasks from pinned public upstream commits."""
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from pathlib import Path


class PrepareError(Exception):
    pass


def _git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode:
        raise PrepareError("upstream Git operation failed; check network access and the pinned commits")
    return result.stdout


def _fetch(repo, source, base, fix):
    _git(repo, "init", "-q")
    _git(repo, "fetch", "-q", "--depth=1", "https://github.com/" + source + ".git", base, fix)
    for sha in (base, fix):
        if _git(repo, "rev-parse", sha + "^{commit}").strip() != sha:
            raise PrepareError("upstream commit did not match the manifest")


def _archive(repo, sha, dest):
    archive = repo.parent / (sha + ".tar")
    _git(repo, "archive", "--format=tar", "--output=" + str(archive), sha)
    dest.mkdir()
    with tarfile.open(archive) as data:
        data.extractall(dest, filter="data")


def _path(value):
    p = Path(value)
    if p.is_absolute() or ".." in p.parts or not p.parts or ".git" in p.parts:
        raise PrepareError("snapshot paths must stay inside their task directory")
    return p


def prepare_task(template, tasks_dir, cache_dir=None):
    """Build a new user task without overwriting existing work. No models run."""
    template, tasks_dir = Path(template), Path(tasks_dir).expanduser()
    meta = tomllib.loads((template / "task.toml").read_text())
    task_id = meta["id"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", task_id):
        raise PrepareError("invalid task identifier")
    final = tasks_dir / task_id
    if final.exists():
        raise PrepareError("task already exists; choose another task directory to preserve it")
    if (template / "data_recipe.toml").is_file():
        cache = Path(cache_dir or Path.home() / ".cache" / "agentbench" / "inputs")
        result = subprocess.run(
            [sys.executable, str(template / "prepare.py"), "--tasks-dir", str(tasks_dir),
             "--cache-dir", str(cache)], capture_output=True, text=True,
        )
        if result.returncode:
            raise PrepareError("data preparation failed; check network access, input checksums and destination (existing work preserved)")
        return tasks_dir / meta["id"]
    recipe = tomllib.loads((template / "snapshot.toml").read_text())
    source, base, fix = recipe["source_repo"], recipe["base_commit"], recipe["fix_commit"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", source) or not all(
        re.fullmatch(r"[0-9a-f]{40}", value) for value in (base, fix)
    ):
        raise PrepareError("snapshot source must name a public repository and full pinned commits")
    tasks_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".prepare-", dir=tasks_dir) as name:
        temp = Path(name)
        upstream = temp / "upstream"
        upstream.mkdir()
        _fetch(upstream, source, base, fix)
        start, fixed = temp / "start", temp / "fixed"
        _archive(upstream, base, start)
        _archive(upstream, fix, fixed)
        task = temp / "task"
        shutil.copytree(template, task)
        (task / "snapshot.toml").unlink()
        # A template may retain historical notices without bundling source code.
        shutil.copytree(start, task / "repo", dirs_exist_ok=True)
        for value in recipe.get("exclude", []):
            target = task / "repo" / _path(value)
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink(missing_ok=True)
        for row in recipe.get("hidden_files", []):
            src = fixed / _path(row["from"])
            target = task / "hidden" / _path(row["to"])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, target)
        if recipe.get("pristine_tests"):
            shutil.copytree(task / "repo/tests", task / "hidden/tests")
        for value in recipe["gold_paths"]:
            rel = _path(value)
            target = task / "gold" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(fixed / rel, target)
        if recipe.get("version_stub"):
            (task / "repo/src/humanize/_version.py").write_text('__version__ = "0.0.0"\n')
        if final.exists():
            raise PrepareError("task appeared during preparation; existing work preserved")
        task.rename(final)
    return final
