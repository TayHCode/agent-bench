#!/usr/bin/env python3
"""A stand-in for the `claude` CLI: no model, no network. Point AGENTBENCH_CLAUDE_BIN at this file.

The runner passes the CLI almost no environment, so settings come from a JSON file next to this script
(<this file>.json), keys:
  fix_dir   folder whose files are copied into the working directory (the "agent's fix")
  command   a shell command the "agent" claims to have run (for the peek flag)
  tokens    fresh tokens to report (default 1000)
  model     model name to report (default claude-haiku-5-5)
  sleep     seconds to idle before finishing
Standard library only.
"""
import json
import os
import shutil
import sys
import time


def emit(o):
    print(json.dumps(o), flush=True)


cfg = {}
if os.path.exists(__file__ + ".json"):
    with open(__file__ + ".json") as f:
        cfg = json.load(f)
sys.stdin.read()  # the prompt
emit({"type": "system", "subtype": "init"})
for noise in cfg.get("json_noise", []):
    emit(noise)
fix = cfg.get("fix_dir")
if fix:
    shutil.copytree(fix, ".", dirs_exist_ok=True)
if cfg.get("command"):
    emit({"type": "assistant", "message": {"id": "m0", "model": "claude-haiku-5-5", "content": [
        {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": cfg["command"]}}],
        "usage": {"input_tokens": 1, "cache_creation_input_tokens": 1, "cache_read_input_tokens": 0, "output_tokens": 1}}})
time.sleep(float(cfg.get("sleep", 0)))
n = int(cfg.get("tokens", 1000))
model = cfg.get("model", "claude-haiku-5-5")
emit({"type": "assistant", "message": {"id": "m1", "model": model, "content": [{"type": "text", "text": "done"}],
      "usage": {"input_tokens": 10, "cache_creation_input_tokens": n, "cache_read_input_tokens": 0, "output_tokens": 50}}})
time.sleep(float(cfg.get("sleep_after_usage", 0)))
emit({"type": "result", "subtype": "success", "is_error": False, "duration_ms": 10, "duration_api_ms": 5, "total_cost_usd": 0.0,
      "modelUsage": {model: {"inputTokens": 10, "cacheCreationInputTokens": n, "cacheReadInputTokens": 0, "outputTokens": 50}}})
