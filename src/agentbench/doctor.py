"""`agentbench doctor`: is this machine ready, and if not, the exact command that fixes each problem.

Every check is cheap and free: versions, `claude auth status`, `codex login status`, free disk space. Nothing here
calls a model. A problem is a BLOCKER only if it stops what was asked for (Python, git, disk; with `needs`, the
agents you chose); a missing optional agent CLI is a note.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from .runner import claude_bin, codex_bin
from .tasks import agentbench_home

MIN_PYTHON = (3, 11)
BLOCK_BELOW_MB, WARN_BELOW_MB = 200, 2000
INSTALL = {"claude-code": "npm install -g @anthropic-ai/claude-code", "codex": "npm install -g @openai/codex"}
LOGIN = {"claude-code": "claude auth login", "codex": "codex login"}


def check(level, name, detail, fix=None):
    return {"level": level, "name": name, "detail": detail, "fix": fix}  # level: ok | note | blocker


def git_fix():
    if sys.platform == "darwin":
        return "xcode-select --install"
    if sys.platform.startswith("win"):
        return "agentbench needs WSL on Windows: run `wsl --install`, then work inside WSL"
    return "sudo apt install git   (or your distro's package manager)"


def run_quiet(argv, timeout=20):
    """(exit code, output) of a short command; (None, reason) if it cannot run."""
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return None, "timed out"
    except OSError as e:
        return None, e.strerror or str(e)
    return r.returncode, (r.stdout + r.stderr).strip()


def check_python():
    v = tuple(sys.version_info[:3])
    have = ".".join(map(str, v))
    if v[:2] < MIN_PYTHON:
        return check("blocker", "python", f"Python {have} is too old (need {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+)",
                     "install Python 3.12 (https://www.python.org/downloads/ or `uv python install 3.12`), then reinstall agentbench with it")
    return check("ok", "python", f"Python {have}")


def check_platform():
    if sys.platform.startswith("win"):
        return check("blocker", "platform", "native Windows is not supported: use WSL (Windows Subsystem for Linux)",
                     "wsl --install   (then open the Ubuntu app and run the same agentbench commands there)")
    return check("ok", "platform", f"{platform.system()}")


def check_git():
    if not shutil.which("git"):
        return check("blocker", "git", "git is not installed", git_fix())
    return check("ok", "git", run_quiet(["git", "--version"])[1] or "git found")


def check_disk(path=None):
    path = Path(path or agentbench_home())
    while not path.exists() and path != path.parent:
        path = path.parent
    free_mb = shutil.disk_usage(path).free // (1024 * 1024)
    if free_mb < BLOCK_BELOW_MB:
        return check("blocker", "disk", f"only {free_mb} MB free (each run copies the repository)", "free some space, or point AGENTBENCH_HOME at a bigger disk")
    if free_mb < WARN_BELOW_MB:
        return check("note", "disk", f"{free_mb} MB free: enough for small repositories", "free a few GB before benchmarking a big repository")
    return check("ok", "disk", f"{free_mb / 1024:.0f} GB free")


def claude_login():
    """(logged in or None when unknown, how)."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return True, "ANTHROPIC_API_KEY is set"
    code, out = run_quiet([claude_bin(), "auth", "status"])
    if code is None:
        return None, out
    try:
        info = json.loads(out)
    except json.JSONDecodeError:
        info = None
    if isinstance(info, dict) and "loggedIn" in info:
        return bool(info["loggedIn"]), info.get("authMethod") or "logged in"
    return (True, "logged in") if code == 0 else (False, "not logged in")


def codex_login():
    code, out = run_quiet([codex_bin(), "login", "status"])
    if code is None:
        return None, out
    return code == 0 and "not logged in" not in out.lower(), out.splitlines()[0] if out else ""


def check_agent(cli, needed):
    """One agent CLI: installed? logged in? `needed` makes a problem a blocker (otherwise a note)."""
    level = "blocker" if needed else "note"
    exe = claude_bin() if cli == "claude-code" else codex_bin()
    name = "claude" if cli == "claude-code" else "codex"
    if not (shutil.which(exe) or Path(exe).is_file()):
        return check(level, name, f"{name} is not installed", INSTALL[cli])
    code, out = run_quiet([exe, "--version"])
    if code != 0:  # e.g. a Windows install seen from WSL that cannot find node
        return check(level, name, f"{name} was found but does not run ({(out or 'no output').splitlines()[0][:80]})", INSTALL[cli])
    ver = out.splitlines()[:1]
    label = (ver[0] if ver[0].startswith(name) else f"{name} {ver[0]}") if ver else name
    ok, how = claude_login() if cli == "claude-code" else codex_login()
    if ok is None:
        return check("note", name, f"{label}: could not tell whether it is logged in ({how})", f"run `{LOGIN[cli]}` if a real run says you are logged out")
    if not ok:
        return check(level, name, f"{label} is installed but not logged in", LOGIN[cli])
    return check("ok", name, f"{label}: logged in ({how})")


def diagnose(needs=(), disk_path=None):
    """All checks. needs: agent CLIs ('claude-code', 'codex') the coming run depends on; a problem with those is a blocker."""
    results = [check_platform(), check_python(), check_git(), check_disk(disk_path)]
    results += [check_agent(cli, cli in needs) for cli in ("claude-code", "codex")]
    if not shutil.which("uv"):
        results.append(check("note", "uv", "uv is not installed (only needed for tasks whose checks use it, such as the built-in code tasks)",
                             "curl -LsSf https://astral.sh/uv/install.sh | sh"))
    return results


def available_agents(results):
    """CLIs that are installed and logged in, from diagnose() results."""
    names = {"claude": "claude-code", "codex": "codex"}
    return [names[r["name"]] for r in results if r["name"] in names and r["level"] == "ok"]


def blockers(results):
    return [r for r in results if r["level"] == "blocker"]


def display(results):
    mark = {"ok": "ok     ", "note": "note   ", "blocker": "BLOCKER"}
    lines = [f"agentbench doctor ({platform.system()}, Python {platform.python_version()})"]
    for r in results:
        lines.append(f"  {mark[r['level']]} {r['name']}: {r['detail']}")
        if r["fix"]:
            lines.append(f"          fix: {r['fix']}")
    bad, agents = blockers(results), available_agents(results)
    if bad:
        lines.append("Not ready: fix the BLOCKER line(s) above, then run `agentbench doctor` again.")
    elif agents:
        lines.append(f"Ready. Real runs are possible with: {', '.join(agents)}. Try `agentbench demo`, then `agentbench start`.")
    else:
        lines.append("Ready for `agentbench demo` (free). For real runs, install and log in to claude or codex (see the fix lines above).")
    return "\n".join(lines)


def main(needs=()):
    results = diagnose(needs)
    print(display(results))
    return 1 if blockers(results) else 0
