"""`agentbench task from-commit`: turn a past fix in your own repo into a private, verified task folder.

Nothing here talks to a network or a model. The task is built from `git` objects only: the fix commit's parent becomes
`repo/` (one commit, no remotes, no later history), the commit's test files become `hidden/overlay/`, the rest of the
commit becomes `gold/`.
"""

import fnmatch
import json
import re
import shlex
import shutil
import subprocess
import tarfile
import tomllib
from datetime import date
from pathlib import Path

from .tasks import is_test_path, verify_task

# Files that are left out of repo/ (and gold/, hidden/) whatever they contain.
SECRET_FILES = (".env", ".env.*", "*.pem", "id_*", "credentials*", ".netrc", "*.p12", "*.pfx")
SECRET_PATTERNS = {
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "private key block": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY"),
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})"),
    "Slack token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    "API key (sk-...)": re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{24,}"),
    "Stripe key": re.compile(r"\b[sr]k_live_[A-Za-z0-9]{16,}"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "JSON web token": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    "password or secret assignment": re.compile(
        r"""(?ix)\b(?:api[_-]?key|secret(?:[_-]?key)?|access[_-]?token|auth[_-]?token|password|passwd)\b["']?\s*[:=]\s*["']([^"'\s]{12,})["']"""),
}
PLACEHOLDER = re.compile(r"(?i)example|changeme|placeholder|your[_-]|xxxx|\*{4}|<|\$\{|\{\{|test|dummy|fake|redacted")
MAX_SCAN_BYTES = 1_000_000


class BuildError(Exception):
    pass


def git(repo, *args, check=True, text=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=text)
    if check and r.returncode != 0:
        raise BuildError(f"git {args[0]} failed: {(r.stderr if text else r.stderr.decode(errors='replace')).strip()[:300]}")
    return r.stdout


def resolve(repo, fix, base=None):
    sha = git(repo, "rev-parse", "--verify", "--quiet", f"{fix}^{{commit}}", check=False).strip()
    if not sha:
        raise BuildError(f"{fix!r} is not a commit in that repository")
    parents = git(repo, "rev-list", "--parents", "-n", "1", sha).split()[1:]
    if base:
        base_sha = git(repo, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}", check=False).strip()
        if not base_sha:
            raise BuildError(f"--base {base!r} is not a commit in that repository")
        return sha, base_sha
    if len(parents) > 1:
        raise BuildError("that is a merge commit; pass --base <commit> to say which tree the agent starts from")
    if not parents:
        raise BuildError("that is the first commit of the repository, so there is no parent to start from")
    return sha, parents[0]


def changed(repo, base, fix):
    """[(status, mode, path)] between base and fix, renames shown as a delete plus an add."""
    raw = git(repo, "diff", "--raw", "--no-renames", "-z", "--no-abbrev", base, fix).split("\0")
    out, i = [], 0
    while i + 1 < len(raw) and raw[i].startswith(":"):
        meta = raw[i].split()
        out.append((meta[4][0], meta[1], raw[i + 1]))
        i += 2
    return out


def is_secret_file(path):
    name = path.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatch(name, pat) for pat in SECRET_FILES)


def extract_parent(repo, base, dest):
    """git archive of `base` into dest. Returns paths skipped (unsafe links)."""
    dest.mkdir(parents=True)
    skipped = []
    proc = subprocess.Popen(["git", "-C", str(repo), "archive", "--format=tar", base], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    with proc.stdout, tarfile.open(fileobj=proc.stdout, mode="r|") as tf:
        for m in tf:
            try:
                tf.extract(m, dest, filter="data")
            except (tarfile.FilterError, OSError):
                skipped.append(m.name)
    err = proc.stderr.read().decode(errors="replace")
    proc.stderr.close()
    if proc.wait() != 0:
        raise BuildError("git archive failed: " + err[:300])
    return skipped


def remove_secret_files(root):
    gone = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and not p.is_symlink() and is_secret_file(p.name):
            gone.append(p.relative_to(root).as_posix())
            p.unlink()
    return gone


def scan_secrets(*roots):
    """[(path, line, kind)] of secret-shaped strings. Values are never returned, so they can never be printed."""
    hits = []
    for root in roots:
        for p in sorted(root.rglob("*")):
            if not p.is_file() or p.is_symlink() or p.stat().st_size > MAX_SCAN_BYTES:
                continue
            data = p.read_bytes()
            if b"\0" in data:
                continue
            for n, line in enumerate(data.decode(errors="replace").splitlines(), 1):
                for kind, rx in SECRET_PATTERNS.items():
                    m = rx.search(line)
                    if m and not (kind.startswith("password") and PLACEHOLDER.search(m.group(1))):
                        hits.append((p.relative_to(root.parent).as_posix(), n, kind))
    return hits


def _has(root, *names):
    return any((root / n).exists() for n in names)


def guess_check(repo_dir, test_files):
    """(setup argv or None, check argv, label) from what the repo contains. A guess: --check and --setup override it."""
    exts = {Path(t).suffix for t in test_files}
    pj = repo_dir / "package.json"
    if exts & {".py"}:
        uv = (repo_dir / "uv.lock").exists()
        base = ["uv", "run", "--", "python", "-m", "pytest"] if uv else ["python3", "-m", "pytest"]
        return (["uv", "sync"] if uv else None), [*base, "-q", "-x", *test_files], "pytest"
    if exts & {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"} and pj.exists() and "test" in (json.loads(pj.read_text() or "{}").get("scripts") or {}):
        install = ["npm", "ci"] if (repo_dir / "package-lock.json").exists() else ["npm", "install", "--no-audit", "--no-fund"]
        return install, ["npm", "test", "--", *test_files], "npm test"
    if ".go" in exts and (repo_dir / "go.mod").exists():
        pkgs = sorted({"./" + (str(Path(t).parent) if str(Path(t).parent) != "." else "") for t in test_files})
        return None, ["go", "test", *[p.rstrip("/") or "." for p in pkgs]], "go test"
    if ".rs" in exts and (repo_dir / "Cargo.toml").exists():
        return None, ["cargo", "test", "--quiet"], "cargo test"
    mk = repo_dir / "Makefile"
    if mk.exists() and re.search(r"(?m)^test\s*:", mk.read_text(errors="replace")):
        return None, ["make", "test"], "make test"
    raise BuildError("could not guess how this repository runs tests (looked for pytest, npm test, go test, cargo test, "
                     "make test); pass --check 'COMMAND' (and --setup 'COMMAND' if it needs an install)")


def draft_prompt(subject, body, check_label):
    body = "\n".join(l for l in body.splitlines() if not re.match(r"(?i)^(signed-off-by|co-authored-by|reviewed-by|change-id):", l)).strip()
    return ("<!-- DRAFT: rewrite this to say what is wrong, not how it was fixed. Delete this line when done; "
            "`agentbench run` refuses to start while it is here. -->\n"
            f"{subject}\n\n" + (f"{body}\n\n" if body else "")
            + "Run the project's existing tests before you finish.\n")


def prompt_leaks(prompt, fix_sha, hidden_paths):
    """Warnings for a prompt that quotes the fix commit or names the hidden tests."""
    warn = []
    for tok in re.findall(r"\b[0-9a-f]{7,40}\b", prompt):
        if fix_sha.startswith(tok):
            warn.append("prompt.md contains the fix commit's SHA")
    names = {Path(p).name for p in hidden_paths} | {Path(p).stem for p in hidden_paths}
    for n in sorted(names):
        if len(n) > 3 and n in prompt:
            warn.append(f"prompt.md names the hidden test file {n!r}")
    return warn


def toml_str(s):
    return json.dumps(s)  # JSON strings are valid TOML basic strings


def toml_list(items):
    return "[" + ", ".join(toml_str(i) for i in items) + "]"


def build(repo, fix, task_id, tasks_dir, base=None, check=None, setup=None, allow_secrets=False, keep_failed=False, out=print):
    """Build and verify one task. Returns (exit code, task folder or None)."""
    repo, tasks_dir = Path(repo).expanduser().resolve(), Path(tasks_dir).expanduser()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", task_id):
        raise BuildError("--id may only hold letters, digits, dot, dash and underscore")
    final = tasks_dir / task_id
    if final.exists():
        raise BuildError(f"task {task_id!r} already exists in the tasks folder; pick another --id or delete it")
    if not repo.is_dir() or git(repo, "rev-parse", "--git-dir", check=False).strip() == "":
        raise BuildError("that is not a git repository")
    sha, base_sha = resolve(repo, fix, base)
    subject = git(repo, "log", "-1", "--format=%s", sha).strip()
    body = git(repo, "log", "-1", "--format=%b", sha)
    commit_date = git(repo, "log", "-1", "--format=%cs", sha).strip()
    remote = re.sub(r"^(\w+://)[^/@]*@", r"\1", git(repo, "remote", "get-url", "origin", check=False).strip())  # never keep a token
    if "://" not in remote and "@" not in remote:
        remote = ""  # a local path says nothing an agent could look up
    files = changed(repo, base_sha, sha)

    test_rows = [(s, m, p) for s, m, p in files if s in "AM" and is_test_path(p) and not is_secret_file(p)]
    tests = [p for _, _, p in test_rows]
    golds = [(s, m, p) for s, m, p in files if not is_test_path(p) and not is_secret_file(p)]
    if not tests:
        raise BuildError("this commit changes no test files (paths under tests/, test_*.py, *.test.ts, ...), so there is no "
                         "check to hide. Use a command task instead (see the README, 'Other task kinds').")
    if not golds:
        raise BuildError("this commit only changes tests; there is no fix to hide in gold/")
    build_dir = tasks_dir / f".{task_id}.building"
    shutil.rmtree(build_dir, ignore_errors=True)
    build_dir.mkdir(parents=True)
    try:
        skipped = extract_parent(repo, base_sha, build_dir / "repo")
        removed = remove_secret_files(build_dir / "repo")
        for status, mode, path in golds:
            if status == "D":
                continue
            if mode in ("120000", "160000"):
                skipped.append(path)
                continue
            _write_blob(repo, sha, path, build_dir / "gold" / path, mode)
        for _, mode, path in test_rows:
            if mode not in ("120000", "160000"):
                _write_blob(repo, sha, path, build_dir / "hidden" / "overlay" / path, mode)
        gold_delete = [p for s, m, p in golds if s == "D"]
        gold_files = [p for s, m, p in golds if s != "D" and p not in skipped]
        if not gold_files and not gold_delete:
            raise BuildError("the non-test part of this commit is empty after leaving out secrets and links")
        setup_cmd, check_cmd, label = guess_check(build_dir / "repo", tests)
        if check:
            check_cmd, label = shlex.split(check), "your --check"
        if setup:
            setup_cmd = shlex.split(setup)
        out(f"files: {sum(1 for _ in (build_dir / 'repo').rglob('*') if _.is_file())} in repo/, {len(gold_files)} in gold/, "
            f"{len(tests)} hidden test file(s); check guessed from the repo: {label}")
        if removed or skipped:
            out(f"left out: {len(removed)} secret-named file(s), {len(skipped)} link(s)/submodule(s)")

        hits = scan_secrets(build_dir / "repo", build_dir / "gold", build_dir / "hidden")
        if hits and not allow_secrets:
            out("REFUSING to build: secret-shaped strings found (anything in repo/ is readable by the agent and goes to its vendor).")
            for path, line, kind in hits[:15]:
                out(f"  {path}:{line}  {kind}")
            out("Remove them, build from a commit without them, or pass --allow-secrets if you accept that.")
            shutil.rmtree(build_dir)
            return 3, None
        if hits:
            out(f"WARNING: {len(hits)} secret-shaped string(s) kept because of --allow-secrets")

        prompt = draft_prompt(subject, body, label)
        (build_dir / "prompt.md").write_text(prompt)
        for w in prompt_leaks(prompt, sha, tests):
            out(f"WARNING: {w}")
        (build_dir / "LICENSE-SOURCE").write_text("Private repository of the person running agentbench. Not for redistribution.\n")
        (build_dir / "task.toml").write_text(
            f"id = {toml_str(task_id)}\ntitle = {toml_str(subject)}\ncategory = \"fix\"\nsource = \"local\"\nlicence = \"private\"\n"
            f"created = {toml_str(date.today().isoformat())}\nprompt = \"prompt.md\"\n"
            + (f"setup = {toml_list(setup_cmd)}\nsetup_timeout = 600\n" if setup_cmd else "")
            + f"check = {toml_list(check_cmd)}\ncheck_timeout = 300\n"
            + (f"gold_delete = {toml_list(gold_delete)}\n" if gold_delete else ""))
        (build_dir / "manifest.toml").write_text(
            f"# Source manifest for {task_id}. Private: do not publish this folder.\nid = {toml_str(task_id)}\nprivate = true\n"
            f"base_commit = {toml_str(base_sha)}\nfix_commit = {toml_str(sha)}\nfix_date = {toml_str(commit_date)}\n"
            + (f"remote_url = {toml_str(remote)}\n" if remote else "")
            + "# If the repository is public, the fix is online and a model may know it: set public_fix = true.\npublic_fix = false\n"
            + f"hidden_check = {toml_str('Test files from the fix commit, copied over the working tree after the run: ' + ', '.join(tests))}\n")
    except Exception:
        if not keep_failed:
            shutil.rmtree(build_dir, ignore_errors=True)
        raise

    task = tomllib.loads((build_dir / "task.toml").read_text()) | {"root": build_dir}
    task["prompt_text"] = prompt
    out(f"verifying (setup once per copy, then the check twice on the unfixed and twice on the fixed tree) ...")
    res = verify_task(task, build_dir / ".verify", repeats=2)
    shutil.rmtree(build_dir / ".verify", ignore_errors=True)
    if res["setup_failed"]:
        return _reject(build_dir, keep_failed, out, "the setup command failed", res["setup_output_tail"])
    if res["flaky"]:
        return _reject(build_dir, keep_failed, out, "REJECTED: flaky. The same tree gave different check results on two runs.",
                       res["start_output_tail"] + "\n---\n" + res["gold_output_tail"])
    if not res["start_fails"]:
        return _reject(build_dir, keep_failed, out, "REJECTED: the new tests PASS on the unfixed tree, so the check proves nothing.",
                       res["start_output_tail"])
    if not res["gold_passes"]:
        return _reject(build_dir, keep_failed, out, "REJECTED: the new tests FAIL on the fixed tree (missing install, services, or the wrong check "
                       "command?). Try --setup / --check.", res["gold_output_tail"])
    build_dir.rename(final)
    out(f"verified: unfixed fails, fixed passes, both twice; the check takes {res['check_seconds']:.1f} s")
    out("The unfixed run failed with:\n" + "\n".join("    " + l for l in res["start_output_tail"].strip().splitlines()[-6:]))
    out("NEXT: edit prompt.md (say what is wrong, not how it was fixed; delete the DRAFT line). This task is private: "
        "the agent can read everything in repo/, and its vendor receives what it reads.")
    return 0, final


def _reject(build_dir, keep, out, why, tail):
    out(why)
    out("\n".join("    " + l for l in tail.strip().splitlines()[-12:]))
    if keep:
        out(f"kept for inspection: {build_dir.name}")
    else:
        shutil.rmtree(build_dir, ignore_errors=True)
    return 4, None


def _write_blob(repo, rev, path, dest, mode):
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", f"{rev}:{path}"], capture_output=True)
    if data.returncode != 0:
        raise BuildError(f"cannot read {path} at the fix commit")
    dest.write_bytes(data.stdout)
    if mode == "100755":
        dest.chmod(0o755)
