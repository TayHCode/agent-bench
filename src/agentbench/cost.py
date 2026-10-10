"""Dollar-equivalent from token counts and the dated public price table."""

import tomllib
from pathlib import Path

_PRICES = None


def load_prices(path=None):
    global _PRICES
    if path is not None:
        return tomllib.loads(Path(path).read_text())
    if _PRICES is None:
        _PRICES = tomllib.loads((Path(__file__).parent / "prices.toml").read_text())
    return _PRICES


def usd(model, tokens, prices=None, prompt_tokens=None):
    """USD for one model's tokens.

    tokens keys: input (uncached), cache_write (1-hour tier), cache_write_5m, cache_read, output.
    prompt_tokens: largest single prompt, used for the long-context tier (Haiku).
    """
    prices = prices or load_prices()
    p = prices["models"].get(model)
    if p is None:
        raise KeyError(f"no price for model {model!r} in table {prices['version']}")
    total = (
        tokens.get("input", 0) * p["input"]
        + tokens.get("cache_write", 0) * p["cache_write"]
        + tokens.get("cache_write_5m", 0) * p.get("cache_write_5m", p["cache_write"])
        + tokens.get("cache_read", 0) * p["cache_read"]
        + tokens.get("output", 0) * p["output"]
    ) / 1_000_000
    over = p.get("long_context_over")
    if over and prompt_tokens and prompt_tokens > over:
        total *= p["long_context_multiplier"]
    return total
