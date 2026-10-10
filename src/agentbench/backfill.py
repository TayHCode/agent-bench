"""Add fields to run.json files written before the runner recorded them (per-file diff, worker count)."""

import json
from pathlib import Path

from .runner import count_workers
from .tasks import diff_summary


def backfill(runs_dir="runs"):
    """Returns the number of run.json files changed. Reads each run's own saved checkout; never reruns anything."""
    changed = 0
    for path in sorted(Path(runs_dir).glob("*/run.json")):
        rec = json.loads(path.read_text())
        work, before = path.parent / "work", json.dumps(rec, sort_keys=True)
        if "files" not in rec["diff"] and (work / ".git").exists():
            rec["diff"] = diff_summary(work, stage=False)
        if "workers" not in rec:
            rec["workers"] = ((rec.get("subagents") or {}).get("spawned") or count_workers(path.parent / "home")) if rec.get("team") else 0
        if json.dumps(rec, sort_keys=True) != before:
            path.write_text(json.dumps(rec, indent=2) + "\n")
            changed += 1
    return changed
