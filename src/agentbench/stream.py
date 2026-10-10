"""Live meters: running token/dollar totals so a cap can kill a run mid-flight.

Claude Code: the stdout stream plus the session files in the clean HOME. Sub-agent calls are not
printed on stdout but are written to `subagents/*.jsonl` under the same projects folder, so tailing the
files is what makes a team run's spend visible while it runs. Codex: the rollout file in the clean
CODEX_HOME, which carries a cumulative `token_count` after every model call.
"""

import json
import re
import threading
from pathlib import Path

from .cost import usd


FRESH = ("input", "cache_write", "cache_write_5m", "output")  # everything except cache reads


def fresh_of(tokens):
    """Tokens that were not served from the cache: input, cache writes and output."""
    return sum(tokens.get(k, 0) for k in FRESH)


def _breach(total, fresh, usd_now, max_tokens, max_usd, max_fresh):
    if max_tokens and total > max_tokens:
        return f"tokens {total} > {max_tokens}"
    if max_fresh and fresh > max_fresh:
        return f"fresh tokens {fresh} > {max_fresh}"
    if max_usd and usd_now > max_usd:
        return f"usd {usd_now:.4f} > {max_usd}"
    return None


def _tok(u):
    cc = u.get("cache_creation") or {}
    w5, w1 = cc.get("ephemeral_5m_input_tokens", 0), cc.get("ephemeral_1h_input_tokens", 0)
    if not cc:  # split unknown: price all writes at the dearer 1-hour tier
        w1 = u.get("cache_creation_input_tokens", 0)
    return {"input": u.get("input_tokens", 0), "cache_write": w1, "cache_write_5m": w5,
            "cache_read": u.get("cache_read_input_tokens", 0), "output": u.get("output_tokens", 0)}


def _read_new(path, offsets):
    """New complete lines of a growing file since the last call."""
    try:
        with open(path, "rb") as f:
            f.seek(offsets.get(path, 0))
            data = f.read()
    except OSError:
        return []
    end = data.rfind(b"\n") + 1
    offsets[path] = offsets.get(path, 0) + end
    return data[:end].decode("utf-8", "replace").splitlines()


class Meter:
    """Claude Code. The authoritative per-model totals still come from the result event (modelUsage)."""

    def __init__(self, prices=None):
        self.prices = prices
        self.by_message = {}  # message id -> (model, tokens); streams repeat ids with growing output
        self.result = None
        self.efforts = set()
        self._offsets = {}
        self._lock = threading.Lock()

    def add(self, mid, model, usage):
        if not usage or not model or model.startswith("<"):
            return
        tok = _tok(usage)
        with self._lock:
            old = self.by_message.get(mid)
            if old is None or sum(tok.values()) >= sum(old[1].values()):
                self.by_message[mid] = (model, tok)

    def feed(self, event):
        msg = event.get("message")
        if event.get("type") == "assistant" and isinstance(msg, dict):
            self.add(msg.get("id") or event.get("uuid") or id(event), msg.get("model"), msg.get("usage"))
        elif event.get("type") == "result":
            self.result = event

    def tail(self, root):
        """Read new lines of every session file (orchestrator and sub-agents) under root."""
        for path in Path(root).rglob("*.jsonl"):
            for line in _read_new(path, self._offsets):
                self.efforts.update(re.findall(r'"perTurnEffort"\s*:\s*"(\w+)"', line))
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = e.get("message")
                if e.get("type") == "assistant" and isinstance(msg, dict):
                    self.add(msg.get("id") or e.get("uuid"), msg.get("model"), msg.get("usage"))

    @property
    def tokens(self):
        return sum(sum(t.values()) for _, t in list(self.by_message.values()))

    @property
    def fresh(self):
        return sum(fresh_of(t) for _, t in list(self.by_message.values()))

    @property
    def usd(self):
        total = 0.0
        for model, t in list(self.by_message.values()):
            try:
                total += usd(model, t, self.prices, prompt_tokens=t["input"] + t["cache_write"] + t["cache_write_5m"] + t["cache_read"])
            except KeyError:
                pass
        return total

    def breach(self, max_tokens, max_usd, max_fresh=None):
        return _breach(self.tokens, self.fresh, self.usd, max_tokens, max_usd, max_fresh)

    def by_model(self):
        """Per-model tokens summed over every call seen (orchestrator and sub-agents)."""
        out = {}
        for model, t in list(self.by_message.values()):
            acc = out.setdefault(model, dict.fromkeys(t, 0))
            for k, v in t.items():
                acc[k] += v
        return out

    def vendor_by_model(self):
        """Per-model tokens as the CLI's own result event reports them (None until it finishes)."""
        if not (self.result and self.result.get("modelUsage")):
            return None
        return {m: {"input": v.get("inputTokens", 0), "cache_write": v.get("cacheCreationInputTokens", 0),
                    "cache_write_5m": 0, "cache_read": v.get("cacheReadInputTokens", 0),
                    "output": v.get("outputTokens", 0)} for m, v in self.result["modelUsage"].items()}

    def max_prompt(self):
        return max((t["input"] + t["cache_write"] + t["cache_write_5m"] + t["cache_read"]
                    for _, t in self.by_message.values()), default=0)


class CodexMeter:
    """Codex CLI: cumulative usage from the rollout file; the model and effort from its turn context."""

    def __init__(self, prices=None, model=None):
        self.prices, self.model = prices, model
        self.total = None  # latest cumulative total_token_usage
        self.efforts, self.models = set(), set()
        self.events, self.final = 0, None
        self._offsets = {}

    def feed(self, event):  # stdout JSONL
        self.events += 1
        if event.get("type") == "turn.completed" and event.get("usage"):
            self.final = event["usage"]

    def tail(self, root):
        for path in Path(root).rglob("rollout-*.jsonl"):
            for line in _read_new(path, self._offsets):
                if '"turn_context"' in line:
                    self.efforts.update(re.findall(r'"effort"\s*:\s*"(\w+)"', line))
                    self.models.update(re.findall(r'"model"\s*:\s*"([\w.\-]+)"', line))
                if '"token_count"' in line:
                    try:
                        info = (json.loads(line).get("payload") or {}).get("info") or {}
                    except json.JSONDecodeError:
                        continue
                    if info.get("total_token_usage"):
                        self.total = info["total_token_usage"]

    def _by_model(self):
        u = self.total or {}
        cached = u.get("cached_input_tokens", 0)
        return {"input": max(u.get("input_tokens", 0) - cached, 0), "cache_write": u.get("cache_write_input_tokens", 0),
                "cache_write_5m": 0, "cache_read": cached, "output": u.get("output_tokens", 0)}

    @property
    def tokens(self):
        return sum(self._by_model().values())

    @property
    def fresh(self):
        return fresh_of(self._by_model())

    @property
    def usd(self):
        try:
            return usd(self.model, self._by_model(), self.prices)
        except KeyError:
            return 0.0

    def breach(self, max_tokens, max_usd, max_fresh=None):
        return _breach(self.tokens, self.fresh, self.usd, max_tokens, max_usd, max_fresh)

    def by_model(self):
        return {self.model: self._by_model()} if self.total else {}

    def vendor_by_model(self):
        return None

    def max_prompt(self):
        return 0

    result = None
