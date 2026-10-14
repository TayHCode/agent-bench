"""contestants.toml: your own model + CLI + effort setups, and the config files each one may see.

    [contestants."haiku-plain"]
    cli = "claude-code"            # claude-code or codex
    model = "claude-haiku-5-5"
    # price_model = "claude-haiku-5-5"  # optional: price the configured model alias with this entry
    effort = "medium"              # optional, default medium
    files = ["my-rules.md"]            # optional: files copied into the clean HOME, nothing else
    # Explicit mappings select the canonical config destination for the chosen CLI.
    # max_usd = 0.5, max_fresh_tokens = 50000, max_minutes = 5   # optional per-contestant caps

    [prices."some-new-model"]      # optional, USD per million tokens, for models prices.toml lacks
    input = 1.0
    output = 5.0
    cache_read = 0.1
    cache_write = 1.25

The first two contestants in the file are the default matrix (put a cheap one first, a strong one second).
"""

import tomllib
from pathlib import Path

from .cost import load_prices
from .fromcommit import is_secret_file
from .stream import CapError, validate_caps

CLIS = ("claude-code", "codex")
KEYS = {"cli", "model", "price_model", "effort", "files", "max_usd", "max_tokens", "max_fresh_tokens", "max_minutes"}
EFFORTS = ("low", "medium", "high", "xhigh", "max")
PRICE_KEYS = ("input", "output", "cache_read", "cache_write")
NEVER_COPY_NAMES = {".credentials.json", "auth.json", ".claude.json", ".netrc", "config.toml"}
NEVER_COPY_DIRS = {".ssh", ".aws", ".gnupg", ".kube", ".docker"}


class ContestantsError(Exception):
    pass


def real_base(cli):
    """Where this CLI keeps its user-level config on the real machine; `files` paths are relative to it."""
    return Path.home() if cli == "claude-code" else Path.home() / ".codex"


def check_file(src, dest, where):
    if not src.is_file():
        raise ContestantsError(f"{where}: {src.name!r} is not a file (copy single files, never a folder or the whole HOME)")
    if is_secret_file(src.name) or src.name in NEVER_COPY_NAMES or NEVER_COPY_DIRS & set(src.parts):
        raise ContestantsError(f"{where}: {src.name!r} looks like a credential or secret and is never copied (the login is linked separately)")
    d = Path(dest)
    if d.is_absolute() or ".." in d.parts or not d.parts:
        raise ContestantsError(f"{where}: destination {dest!r} must be a relative path inside the clean HOME")
    if d.name in NEVER_COPY_NAMES or is_secret_file(d.name):
        raise ContestantsError(f"{where}: destination {dest!r} would replace a login or credentials file")


def parse_files(cid, cli, entries, base_dir):
    out = []
    for e in entries:
        where = f"contestant {cid!r}, files"
        if isinstance(e, str):
            src = Path(e).expanduser()
            src = src if src.is_absolute() else base_dir / src
            try:
                dest = src.resolve().relative_to(real_base(cli).resolve()).as_posix()
            except ValueError:
                raise ContestantsError(f"{where}: {e!r} is not under {real_base(cli)}; write it as {{ from = \"...\", to = \"...\" }}") from None
        elif isinstance(e, dict) and set(e) == {"from", "to"}:
            src = Path(e["from"]).expanduser()
            src = src if src.is_absolute() else base_dir / src
            dest = e["to"]
        else:
            raise ContestantsError(f"{where}: each entry is a path string or {{ from = ..., to = ... }}")
        check_file(src, dest, where)
        out.append((src, dest))
    return out


def load(path):
    """-> (contestants in runner format, prices table with the file's [prices.*] added). Raises ContestantsError."""
    path = Path(path).expanduser()
    try:
        raw = tomllib.loads(path.read_text())
    except OSError as e:
        raise ContestantsError(f"cannot read {path.name}: {e.strerror}") from None
    except tomllib.TOMLDecodeError as e:
        raise ContestantsError(f"{path.name} is not valid TOML: {e}") from None
    prices = {"version": load_prices()["version"], "models": dict(load_prices()["models"])}
    for model, p in (raw.get("prices") or {}).items():
        if not all(isinstance(p.get(k), (int, float)) for k in PRICE_KEYS):
            raise ContestantsError(f"[prices.{model}] needs numeric {', '.join(PRICE_KEYS)} (USD per million tokens)")
        prices["models"][model] = {**p, "cache_write_5m": p.get("cache_write_5m", p["cache_write"])}
    defs = {}
    for cid, c in (raw.get("contestants") or {}).items():
        if unknown := set(c) - KEYS:
            raise ContestantsError(f"contestant {cid!r}: unknown key(s) {sorted(unknown)}; allowed: {sorted(KEYS)}")
        if c.get("cli") not in CLIS:
            raise ContestantsError(f"contestant {cid!r}: cli must be one of {CLIS}")
        if not c.get("model"):
            raise ContestantsError(f"contestant {cid!r}: model is required")
        effort = c.get("effort", "medium")
        if effort not in EFFORTS:
            raise ContestantsError(f"contestant {cid!r}: effort must be one of {EFFORTS}")
        price_model = c.get("price_model", c["model"])
        if price_model not in prices["models"]:
            raise ContestantsError(f"contestant {cid!r}: no price for model {price_model!r}; add a [prices.\"{price_model}\"] table to the file")
        caps = {k: c[k] for k in ("max_usd", "max_tokens", "max_fresh_tokens", "max_minutes") if k in c}
        try:
            validate_caps(caps)
        except CapError as e:
            raise ContestantsError(f"contestant {cid!r}: {e}") from None
        defs[cid] = {"cli": c["cli"], "model": c["model"], "price_model": price_model, "effort": effort, "caps": caps,
                     "files": parse_files(cid, c["cli"], c.get("files", []), path.parent), "user_defined": True}
    if not defs:
        raise ContestantsError(f"{path.name} defines no contestants (add a [contestants.\"name\"] table)")
    return defs, prices
