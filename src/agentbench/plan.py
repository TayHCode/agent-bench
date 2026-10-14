"""`agentbench plan`: what a matrix will run and what it can cost, before anything runs.

Dollars are dollar-equivalents from the dated price table (a subscription is not billed per token, but uses plan limits).
The *expected* figure is the median of your own earlier runs of that contestant if there are any; otherwise a typical small
fix priced from the pilot runs (about 3k input, 10k cache-write, 150k cache-read, 4k output tokens). The *worst case* is every
run hitting its dollar cap; the ledger cap is what actually stops the spend, so the ceiling is the smaller of the two.
"""

import statistics
import sys
import math

from .cost import usd
from .runner import CONTESTANTS, profile_caps

TYPICAL = {"input": 3_000, "cache_write": 10_000, "cache_read": 150_000, "output": 4_000}
ASK_ABOVE = 2.0  # dollars: above this the plan asks yes/no
LEDGER_STOP = 0.9


class PlanError(Exception):
    pass


def expected_each(cid, c, prices, past):
    """(dollars per run, where the figure comes from)."""
    mine = [r["usd_equivalent"] for r in past if r.get("contestant") == cid and r.get("status") == "ok"]
    if mine:
        return statistics.median(mine), f"median of your {len(mine)} earlier run(s)"
    return usd(c["price_model"], TYPICAL, prices), "typical small fix at list price"


def make_plan(tasks, ids, defs, prices, profile, repeats, ledger_cap, past=()):
    defs = defs or CONTESTANTS
    if ledger_cap is None or not math.isfinite(ledger_cap) or ledger_cap <= 0:
        raise PlanError("refusing to plan without --ledger-cap USD: the ledger cap is the most you are willing to spend, "
                        "and the matrix stops when recorded spend gets within 10% of it")
    missing = sorted({defs[i]["price_model"] for i in ids if defs[i]["price_model"] not in prices["models"]})
    if missing:
        raise PlanError(f"no price for model(s) {missing}: add a [prices.\"MODEL\"] table to contestants.toml")
    rows = []
    for cid in ids:
        caps = profile_caps(cid, profile, defs)
        each, source = expected_each(cid, defs[cid], prices, past)
        n = len(tasks) * repeats
        rows.append({"contestant": cid, "runs": n, "cap_usd": caps["max_usd"], "caps": caps, "model": defs[cid]["model"], "cli": defs[cid]["cli"],
                     "expected_each": min(each, caps["max_usd"]), "source": source})
    expected = sum(r["runs"] * r["expected_each"] for r in rows)
    worst = sum(r["runs"] * r["cap_usd"] for r in rows)
    return {"tasks": list(tasks), "repeats": repeats, "rows": rows, "runs": sum(r["runs"] for r in rows), "profile": profile,
            "expected": expected, "worst": worst, "ledger_cap": ledger_cap, "ceiling": min(worst, ledger_cap), "prices": prices["version"]}


def display_plan(p):
    n_c = len(p["rows"])
    out = [f"Plan: {len(p['tasks'])} task(s) x {n_c} contestant(s) x {p['repeats']} repeat(s) = {p['runs']} runs, one at a time",
           "  tasks: " + ", ".join(p["tasks"])]
    for r in p["rows"]:
        token_limit = ", ".join(f"{r['caps'][key]:,} {kind} tokens"
                                for key, kind in (("max_fresh_tokens", "fresh"), ("max_tokens", "total"))
                                if r["caps"].get(key)) or "no token cap"
        out.append(f"  {r['contestant']}: {r['cli']} / {r['model']}, up to ${r['cap_usd']:g}, {r['caps']['max_minutes']:g} min, "
                   f"{token_limit} per run; expected ${r['expected_each']:.3f} a run ({r['source']})")
    out += [f"Dollar-equivalent at list prices ({p['prices']}); a subscription is not billed per token but uses plan limits:",
            f"  expected      about ${p['expected']:.2f}",
            f"  worst case    ${p['worst']:.2f} (every run hits its dollar cap; token and minute caps are listed per contestant above)",
            f"  ledger cap    ${p['ledger_cap']:.2f}: the matrix stops once recorded spend is within 10% of it (${p['ledger_cap'] * LEDGER_STOP:.2f}), "
            f"and each run's cap is cut to what is left",
            f"  so spend stays under about ${p['ceiling']:.2f}"]
    return "\n".join(out)


def confirm(p, yes=False, stdin=None, out=print):
    """True to go ahead. Above $2 of possible spend it asks; with no terminal and no --yes the answer is no."""
    if p["ceiling"] <= ASK_ABOVE:
        return True
    if yes:
        out(f"--yes: going ahead with up to ${p['ceiling']:.2f}")
        return True
    stdin = stdin or sys.stdin
    if not stdin.isatty():
        out(f"This could spend up to ${p['ceiling']:.2f} (more than ${ASK_ABOVE:.0f}). Not on a terminal, so not going ahead: add --yes to accept, or lower --ledger-cap.")
        return False
    out(f"This could spend up to ${p['ceiling']:.2f} dollar-equivalent (more than ${ASK_ABOVE:.0f}). Go ahead? [y/N] ")
    return stdin.readline().strip().lower() in ("y", "yes")
