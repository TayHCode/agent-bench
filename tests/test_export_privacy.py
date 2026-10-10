"""Scan all shipping bytes, including newly added files; exclude generated environments."""
import re
import math
from collections import Counter
import subprocess
import unittest
from pathlib import Path

from agentbench.fromcommit import SECRET_PATTERNS
from agentbench import cost, plan

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = {
    "home path": re.compile(rb"(?i)(?:/(?:home|Users|Volumes)/[^/\s]+|[A-Z]:[\\/]Users[\\/][^\\/\s]+)"),
    "machine name": re.compile(rb"(?i)\b(?:mac|windows|nas|compute|browser)-\d{2}\b"),
    "email": re.compile(rb"[\w.%+-]+@[\w.-]+\.[a-zA-Z]{2,}"),
    "private tooling": re.compile(rb"(?i)(?:project[-_]outlier|agent[-_]bench[-_]private|\.t3(?:/|\\))"),
    "tailnet address": re.compile(rb"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b"),
    "internal tool": re.compile(rb"(?i)\b(?:Fac" + rb"tory|At" + rb"las)\b"),
    "owner username": re.compile(rb"(?i)\btay" + rb"lor\b"),
    "session config path": re.compile(rb"\.(?:t" + rb"3|claude)[/\\]"),
}


def token_shaped(text):
    """Catch unfamiliar high-entropy credentials in addition to provider prefixes."""
    for match in re.finditer(r"[A-Za-z0-9_+/=-]{32,}", text):
        value = match.group()
        if re.fullmatch(r"[0-9a-fA-F]+", value):  # pinned public commit/digest
            continue
        if not all(re.search(pattern, value) for pattern in (r"[a-z]", r"[A-Z]", r"\d")):
            continue
        entropy = -sum((n / len(value)) * math.log2(n / len(value)) for n in Counter(value).values())
        if entropy >= 4.3:
            return True
    return False


def shipping_files():
    result = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--cached", "--others",
                             "--exclude-standard", "-z"], capture_output=True, check=True)
    return sorted({ROOT / p.decode() for p in result.stdout.split(b"\0") if p})


class ExportPrivacyTest(unittest.TestCase):
    def test_legacy_total_token_plan_displays_without_a_fresh_token_cap(self):
        for profile, expected in (("m2", "150,000 total tokens"), ("m3", "400,000 total tokens")):
            value = plan.make_plan(["fda-recalls-clean"], ["haiku-5-5@claude-code"],
                                   None, cost.load_prices(), profile, 1, 1)
            self.assertIn(expected, plan.display_plan(value))

    def test_every_shipping_file_has_no_private_or_token_shaped_strings(self):
        failures = []
        for path in shipping_files():
            if not path.exists():  # staged deletions
                continue
            raw = path.relative_to(ROOT).as_posix().encode() + b"\n" + path.read_bytes()
            for kind, pattern in PRIVATE.items():
                if pattern.search(raw):
                    failures.append((path.relative_to(ROOT).as_posix(), kind))
            text = raw.decode("utf-8", errors="replace")
            for kind, pattern in SECRET_PATTERNS.items():
                # Assignment examples are reviewed by the release audit; this gate
                # also rejects every supported complete provider credential shape.
                if not kind.startswith("password") and pattern.search(text):
                    failures.append((path.relative_to(ROOT).as_posix(), kind))
            if token_shaped(text):
                failures.append((path.relative_to(ROOT).as_posix(), "high-entropy token"))
        self.assertEqual(failures, [], "shipping paths and finding kinds only; values withheld")

    def test_patterns_detect_synthetic_home_machine_email_and_provider_token(self):
        examples = {"home path": b"/" + b"home" + b"/someone/code",
                    "machine name": b"compute" + b"-" + b"01",
                    "email": b"someone" + b"@" + b"example.invalid"}
        for kind, value in examples.items():
            self.assertIsNotNone(PRIVATE[kind].search(value))
        value = "gh" + "p_" + "A" * 36
        self.assertIsNotNone(SECRET_PATTERNS["GitHub token"].search(value))
