"""The Gemini judge backend: the one place in agentbench that uses the network, and only when you choose --judge gemini.

The request is the documented REST call (POST /v1beta/models/MODEL:generateContent, key in the x-goog-api-key header).
The backend reads authentication from an environment variable at call time without storing, printing or writing it to judge.json.
"""

import json
import os
import urllib.error
import urllib.request

from .judge import DEFAULTS, JudgeError

GEMINI_URL = "https://generativelanguage.googleapis.com"


class Gemini:
    """The documented REST call: POST /v1beta/models/MODEL:generateContent with the key in x-goog-api-key."""
    name = "gemini"
    paid = True

    def __init__(self, cfg):
        self.cfg = DEFAULTS | cfg
        self.url_base = self.cfg.get("base_url", GEMINI_URL).rstrip("/")
        self.key_env = self.cfg.get("api_key_env", "GEMINI_API_KEY")
        self.destination = self.url_base

    def preflight(self):
        self.key()

    def model(self):
        return self.cfg.get("model", "gemini-2.5-pro")

    def key(self):
        key = os.environ.get(self.key_env)
        if not key:
            raise JudgeError(f"no API key: set {self.key_env} (nothing is sent without it)")
        return key

    def estimate(self, packet):
        """Upper-ish bound: 3 characters per input token, and the whole max_output_tokens (thinking included) as output."""
        tin = len(packet["prompt"]) // 3 + 1
        return (tin * self.cfg["price_in"] + self.cfg["max_output_tokens"] * self.cfg["price_out"]) / 1e6

    def call(self, packet):
        body = {"contents": [{"role": "user", "parts": [{"text": packet["prompt"]}]}],
                "generationConfig": {"temperature": 0, "seed": packet["seed"], "responseMimeType": "application/json",
                                     "maxOutputTokens": self.cfg["max_output_tokens"]}}
        req = urllib.request.Request(f"{self.url_base}/v1beta/models/{self.model()}:generateContent", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "x-goog-api-key": self.key()})
        try:
            with urllib.request.urlopen(req, timeout=self.cfg["timeout_s"]) as resp:
                d = json.load(resp)
        except urllib.error.HTTPError as e:
            raise JudgeError(f"Gemini API answered HTTP {e.code}: {e.read().decode(errors='replace')[:200]}")
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            raise JudgeError(f"Gemini API call failed: {e}")
        if (d.get("promptFeedback") or {}).get("blockReason"):
            raise JudgeError(f"Gemini blocked the prompt: {d['promptFeedback']['blockReason']}")
        try:
            text = "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"] if not p.get("thought"))
        except (KeyError, IndexError, TypeError):
            raise JudgeError("Gemini answered without a candidate")
        u = d.get("usageMetadata") or {}
        tin, tout = u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)  # thinking is billed as output
        return {"text": text, "tokens_in": tin, "tokens_out": tout,
                "cost_usd": (tin * self.cfg["price_in"] + tout * self.cfg["price_out"]) / 1e6}
