"""The peek flag: did the agent go looking for the answer?

A run is `peeked` when something the agent *did* (a command it ran, a file it opened, a tool input) mentions the task folder,
`hidden/`, `gold/`, the fix commit's SHA, `gh ` (the GitHub CLI) or the repository's remote URL. Text the agent only read
(command output, file contents) is not scanned, because a project's own README may print its own URL. Pure string matching on the
saved transcript; no model decides. Peeked runs are left out of the report's tables.
"""

import json
import os
import re
import tomllib
from pathlib import Path

SKIP_ITEMS = {"agent_message", "reasoning", "user_message"}
OUTPUT_KEYS = {"aggregated_output", "output", "text", "stdout", "stderr"}


def action_text(event):
    """What the agent did in one transcript line (Claude Code stream-json or Codex --json), as a string; '' if nothing."""
    msg = event.get("message")
    if event.get("type") == "assistant" and isinstance(msg, dict):
        return "\n".join(json.dumps(b.get("input", {})) for b in (msg.get("content") or [])
                         if isinstance(b, dict) and b.get("type") == "tool_use")
    item = event.get("item")
    if isinstance(item, dict) and item.get("type") not in SKIP_ITEMS:
        return json.dumps({k: v for k, v in item.items() if k not in OUTPUT_KEYS})
    return ""


def remote_core(url):
    """'git via SSH: org/repo.git' or 'https://github.com/org/repo' -> 'github.com/org/repo' (lower case)."""
    u = re.sub(r"^[a-z][a-z0-9+.-]*://", "", url.strip().lower())
    u = re.sub(r"^[^/@]*@", "", u)
    u = re.sub(r"^([^/:]+):(?!\d)", r"\1/", u)
    return re.sub(r"(\.git)?/*$", "", u)


def facts(task):
    """What identifies the answer for this task: folder path, fix SHA, remote URL core."""
    root = Path(task["root"])
    m = {}
    if (root / "manifest.toml").exists():
        m = tomllib.loads((root / "manifest.toml").read_text())
    remote = m.get("remote_url") or (f"github.com/{m['source_repo']}" if m.get("source_repo") else "")
    folders = {os.path.abspath(root), Path(os.path.abspath(root)).as_posix(), str(root.resolve()), root.resolve().as_posix()}  # macOS: /var is /private/var
    return {"folders": folders, "sha": (m.get("fix_commit") or "").lower(),
            "remote": remote_core(remote) if remote else ""}


def scan_transcript(path, task):
    """Sorted list of signs found in what the agent did; empty = no peek."""
    f, signs = facts(task), set()
    prompt = task.get("prompt_text", "")
    try:
        lines = Path(path).read_text(errors="replace").splitlines()
    except OSError:
        return []
    for line in lines:
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = action_text(ev) if isinstance(ev, dict) else ""
        if not text:
            continue
        if prompt:
            text = text.replace(prompt, "")
        low = text.lower()
        if any(p in text for p in f["folders"]):
            signs.add("task folder")
        if re.search(r"(?<![\w.-])hidden/", low):
            signs.add("hidden/")
        if re.search(r"(?<![\w.-])gold/", low):
            signs.add("gold/")
        if f["sha"] and any(f["sha"].startswith(t) for t in re.findall(r"\b[0-9a-f]{7,40}\b", low)):
            signs.add("fix commit SHA")
        if re.search(r"(?<![\w.-])gh\s+\w", low):
            signs.add("gh")
        if f["remote"] and (f["remote"] in low or f["remote"].replace("/", ":", 1) in low):
            signs.add("repo URL")
    return sorted(signs)
