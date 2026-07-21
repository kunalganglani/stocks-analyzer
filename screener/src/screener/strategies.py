"""Strategy registry — each strategy is an independent lens over a stock.

The daily job evaluates EVERY registered strategy for every screened ticker and
stores the verdicts in daily_screens.strategies, e.g.:

  {"minervini": {"pass": true,  "checks": {...}},
   "buffett":   {"pass": false, "checks": {"positive_fcf": false, ...}}}

The web screener renders one filter chip per registry entry, so adding a new
strategy here (plus META) is all it takes for it to appear in the UI.

NOTE: the BUY confluence gate is unchanged — it still requires the full weekly
quality pass AND Minervini. Strategies here are an exploration/filter layer.
"""

from __future__ import annotations

from .config import T

# key -> human name + one-liner, synced to the `settings.strategies` row so the
# web app can label chips without a redeploy.
META = [
    {
        "key": "minervini",
        "name": "Minervini",
        "description": "Stage-2 uptrend: all 8 Trend Template checks (price above rising long-term averages, near highs, strong vs the market).",
    },
    {
        "key": "buffett",
        "name": "Buffett",
        "description": "Wonderful business: high returns on capital, real free cash flow, growing sales and profits.",
    },
    {
        "key": "munger",
        "name": "Munger",
        "description": "Avoid stupidity: little debt and a durable moat (stable or expanding margins).",
    },
]


def _num(x) -> float | None:
    return None if x is None else float(x)


def evaluate_minervini(tt: dict) -> dict:
    checks = {k: bool(v) for k, v in tt.items() if k != "pass"}
    return {"pass": bool(tt.get("pass")), "checks": checks}


def evaluate_buffett(f: dict | None) -> dict:
    """Profit engine: returns on capital, cash generation, growth.
    Missing fundamentals -> failed checks (conservative, mirrors quality.py)."""
    f = f or {}
    roe, roic = _num(f.get("roe")), _num(f.get("roic"))
    fcf = _num(f.get("fcf"))
    rev_g, eps_g = _num(f.get("rev_growth_3y")), _num(f.get("eps_growth_3y"))
    checks = {
        "returns_on_capital": bool(
            (roe is not None and roe >= T.min_roe) or (roic is not None and roic >= T.min_roic)
        ),
        "positive_free_cash_flow": bool(fcf is not None and fcf > 0),
        "revenue_growing": bool(rev_g is not None and rev_g > 0),
        "earnings_growing": bool(eps_g is not None and eps_g > 0),
    }
    return {"pass": all(checks.values()), "checks": checks}


def evaluate_munger(f: dict | None) -> dict:
    """Discipline and moat: low debt, margins that don't erode."""
    f = f or {}
    de = _num(f.get("debt_to_equity"))
    gm_stdev = _num(f.get("gross_margin_stdev"))
    gm_avg = _num(f.get("gross_margin_avg"))
    gm_latest = _num((f.get("raw") or {}).get("gross_margin_latest"))
    stable = (
        gm_stdev is None  # no gross-profit line (banks etc.) — not held against it
        or gm_stdev <= T.min_gross_margin_stability
        or (gm_latest is not None and gm_avg is not None and gm_latest >= gm_avg)
    )
    checks = {
        "low_debt": bool(de is not None and de < T.max_debt_to_equity),
        "durable_margins": bool(stable),
    }
    return {"pass": all(checks.values()), "checks": checks}


def evaluate_all(tt: dict, fundamentals: dict | None) -> dict:
    """One verdict object per registered strategy."""
    return {
        "minervini": evaluate_minervini(tt),
        "buffett": evaluate_buffett(fundamentals),
        "munger": evaluate_munger(fundamentals),
    }
