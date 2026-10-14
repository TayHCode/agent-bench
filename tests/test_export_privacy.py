"""Scan all shipping bytes, including newly added files; exclude generated environments."""
import re
import json
import os
import tempfile
from unittest.mock import patch
import math
from collections import Counter
import subprocess
import unittest
from pathlib import Path

from agentbench.fromcommit import SECRET_PATTERNS
from agentbench import cost, plan

ROOT = Path(__file__).resolve().parents[1]
IPV4_OCTET = rb'(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])'
PUBLIC_PATTERNS = {
    'home path': re.compile(b'(?i)(?:/(?:home|Users|Volumes)/[^/\\s]+|[A-Z]:[\\\\/]Users[\\\\/][^\\\\/\\s]+)'),
    'email': re.compile(b'[\\w.%+-]+@[\\w.-]+\\.[a-zA-Z]{2,}'),
    'private network address': re.compile(
        rb'(?<![\w.])(?:10(?:\.' + IPV4_OCTET + rb'){3}|'
        rb'(?:192\.168|172\.(?:1[6-9]|2[0-9]|3[01]))(?:\.' + IPV4_OCTET + rb'){2})(?!\w|\.\d)'),
    'local hostname': re.compile(rb'(?i)\b[a-z0-9][a-z0-9_-]*\.(?:local|lan|internal)\b'),
}


def private_patterns(root=ROOT):
    """External JSON array of literal terms; never store the real list in the tree."""
    supplied = os.environ.get("AGENTBENCH_PRIVATE_TERMS_FILE")
    if not supplied:
        return None
    path = Path(supplied).resolve()
    if path.is_relative_to(root.resolve()):
        raise ValueError("private terms file must be outside the repository")
    terms = json.loads(path.read_text())
    if not isinstance(terms, list) or not terms or not all(isinstance(t, str) and t for t in terms):
        raise ValueError("private terms file must contain a nonempty JSON array of nonempty strings")
    return [re.compile(re.escape(t.encode()), re.I) for t in terms]


def term_hits(paths, patterns, root=None):
    return [index for index, path in enumerate(paths)
            if any(pattern.search((path.relative_to(root).as_posix() if root else path.name).encode() + b"\n" + path.read_bytes()) for pattern in patterns)]


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

    def test_shipping_patterns_and_optional_external_private_terms(self):
        patterns = private_patterns()
        if patterns is None:
            print("Privacy mode: synthetic fixture + generic shipping scan; real private-term check NOT run.", flush=True)
            with tempfile.TemporaryDirectory() as tmp:
                fixture = Path(tmp) / "sample.txt"
                fixture.write_text("SYNTHETIC-PRIVATE-ALPHA")
                self.assertEqual(term_hits([fixture], [re.compile(b"synthetic-private-alpha", re.I)]), [0])
        else:
            print("Privacy mode: external private-term list + generic shipping scan.", flush=True)
            paths = [p for p in shipping_files() if p.exists()]
            matched_files = [paths[index].relative_to(ROOT).as_posix() for index in term_hits(paths, patterns, ROOT)]
            self.assertEqual(matched_files, [], "private-term file paths only; matched values withheld")
        failures = []
        for path in shipping_files():
            if not path.exists():  # staged deletions
                continue
            raw = path.relative_to(ROOT).as_posix().encode() + b"\n" + path.read_bytes()
            for kind, pattern in PUBLIC_PATTERNS.items():
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

    def test_external_terms_are_literal_case_insensitive_and_never_loaded_from_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            terms = Path(tmp) / "terms.json"
            terms.write_text(json.dumps(["synthetic.literal+alpha"]))
            fixture = root / "sample.txt"
            fixture.write_text("SYNTHETIC.LITERAL+ALPHA")
            with patch.dict(os.environ, {"AGENTBENCH_PRIVATE_TERMS_FILE": str(terms)}):
                patterns = private_patterns(root)
                self.assertEqual(term_hits([fixture], patterns), [0])
                fixture.write_text("syntheticXliteralalpha")
                self.assertEqual(term_hits([fixture], patterns), [])
            with patch.dict(os.environ, {"AGENTBENCH_PRIVATE_TERMS_FILE": str(fixture)}):
                with self.assertRaisesRegex(ValueError, "outside"):
                    private_patterns(root)

    def test_external_term_failure_names_only_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "sample.txt"
            fixture.write_text("SYNTHETIC-PRIVATE-ALPHA")
            case = ExportPrivacyTest("test_shipping_patterns_and_optional_external_private_terms")
            with (patch(__name__ + ".ROOT", root), patch(__name__ + ".shipping_files", return_value=[fixture]),
                  patch(__name__ + ".private_patterns", return_value=[re.compile(b"SYNTHETIC-PRIVATE-ALPHA")])):
                with self.assertRaises(AssertionError) as failure:
                    case.test_shipping_patterns_and_optional_external_private_terms()
            self.assertIn("sample.txt", str(failure.exception))
            self.assertNotIn("SYNTHETIC-PRIVATE-ALPHA", str(failure.exception))

    def test_patterns_detect_synthetic_home_machine_email_and_provider_token(self):
        examples = {"home path": b"/" + b"home" + b"/someone/code",
                    "email": b"someone" + b"@" + b"example.invalid"}
        for kind, value in examples.items():
            self.assertIsNotNone(PUBLIC_PATTERNS[kind].search(value))
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "synthetic-host-01"
            sample.write_text("synthetic")
            self.assertEqual(term_hits([sample], [re.compile(b"synthetic-host-01")]), [0])
        value = "gh" + "p_" + "A" * 36
        self.assertIsNotNone(SECRET_PATTERNS["GitHub token"].search(value))
