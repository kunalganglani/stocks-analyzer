"""Buffett/Munger quality gate over extracted fundamentals.

Pass requires ALL of:
  - returns on capital: ROE >= 15% OR ROIC >= 12%
  - balance sheet: debt/equity < 1.5
  - real cash: free cash flow > 0
  - growth: multi-year revenue AND eps growth > 0
  - durable moat proxy: gross margin stability (stdev <= threshold), when margins exist

Missing core data (returns, D/E, FCF) or missing growth data -> fail with
'insufficient_data' style reasons; pass-if-unknown is never allowed.
Gross margin is pass-if-absent (financials/REITs report no gross profit).
"""

from __future__ import annotations

from .config import T


def evaluate(f: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    roe, roic = f.get("roe"), f.get("roic")
    if roe is None and roic is None:
        reasons.append("insufficient_data:returns_on_capital")
    elif not ((roe is not None and roe >= T.min_roe)
              or (roic is not None and roic >= T.min_roic)):
        reasons.append(f"low_returns roe={_fmt(roe)} roic={_fmt(roic)}")

    de = f.get("debt_to_equity")
    if de is None:
        reasons.append("insufficient_data:debt_to_equity")
    elif de >= T.max_debt_to_equity:
        reasons.append(f"high_debt de={de:.2f}")

    fcf = f.get("fcf")
    if fcf is None:
        reasons.append("insufficient_data:fcf")
    elif fcf <= 0:
        reasons.append("negative_fcf")

    rev_g, eps_g = f.get("rev_growth_3y"), f.get("eps_growth_3y")
    if rev_g is None:
        reasons.append("insufficient_data:revenue_growth")
    elif rev_g <= 0:
        reasons.append(f"revenue_shrinking {rev_g:.1%}")
    if eps_g is None:
        reasons.append("insufficient_data:eps_growth")
    elif eps_g <= 0:
        reasons.append(f"eps_shrinking {eps_g:.1%}")

    # Margin instability only counts against the moat when it's downside
    # volatility — expanding margins (latest >= average) are a strength.
    gm_stdev = f.get("gross_margin_stdev")
    gm_avg = f.get("gross_margin_avg")
    gm_latest = (f.get("raw") or {}).get("gross_margin_latest")
    if (gm_stdev is not None and gm_stdev > T.min_gross_margin_stability
            and gm_latest is not None and gm_avg is not None and gm_latest < gm_avg):
        reasons.append(f"eroding_margins stdev={gm_stdev:.3f} latest<{gm_avg:.1%}")

    return (len(reasons) == 0, reasons)


def _fmt(x) -> str:
    return "na" if x is None else f"{x:.1%}"
