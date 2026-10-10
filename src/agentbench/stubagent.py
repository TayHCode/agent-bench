"""A stand-in agent for `agentbench demo` and the tests: no model, no network, no cost.

The runner starts it in place of the Claude Code CLI for the built-in `stub-*` contestants and speaks the same
stream-json protocol. AGENTBENCH_STUB_FIX names a folder whose files are copied over the working directory (the stub's
"fix"); unset or empty, it changes nothing. AGENTBENCH_STUB_TOKENS is the fresh-token count it reports.
It checks the runner, not model ability.
"""

import json
import os
import shutil
import sys

MODEL = "agentbench-stub"


def emit(event):
    print(json.dumps(event), flush=True)


def main():
    sys.stdin.read()  # the prompt
    emit({"type": "system", "subtype": "init"})
    fix = os.environ.get("AGENTBENCH_STUB_FIX")
    if fix:
        shutil.copytree(fix, ".", dirs_exist_ok=True)
    n = int(os.environ.get("AGENTBENCH_STUB_TOKENS") or 1000)
    emit({"type": "assistant", "message": {"id": "m1", "model": MODEL, "content": [{"type": "text", "text": "done"}],
          "usage": {"input_tokens": 10, "cache_creation_input_tokens": n, "cache_read_input_tokens": 0, "output_tokens": 50}}})
    emit({"type": "result", "subtype": "success", "is_error": False, "duration_ms": 10, "duration_api_ms": 5, "total_cost_usd": 0.0,
          "modelUsage": {MODEL: {"inputTokens": 10, "cacheCreationInputTokens": n, "cacheReadInputTokens": 0, "outputTokens": 50}}})
    return 0


if __name__ == "__main__":
    sys.exit(main())
