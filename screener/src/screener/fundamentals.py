"""Per-ticker fundamental extraction from yfinance (weekly job).

Everything is best-effort: yfinance fundamentals are patchy, so each metric is
None when unavailable and quality.py decides what missing data means.
"""

from __future__ import annotations

import logging
import math

import pandas as pd
import yfinance as yf

log = logging.getLogger(__name__)


def _sanitize(obj):
    """Recursively replace non-finite floats (inf/nan) with None — they are not
    JSON-serializable and one bad ticker must not sink a whole upsert batch."""
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


def _row(df: pd.DataFrame | None, *names: str) -> pd.Series | None:
    if df is None or df.empty:
        return None
    for n in names:
        if n in df.index:
            s = df.loc[n].dropna()
            if not s.empty:
                return s.sort_index()  # oldest -> newest
    return None


def _cagr(series: pd.Series | None, min_years: int = 2) -> float | None:
    """CAGR oldest->newest over up to 4 annual columns; sign-safe fallback."""
    if series is None or len(series) < min_years:
        return None
    first, last = float(series.iloc[0]), float(series.iloc[-1])
    years = len(series) - 1
    if first <= 0:
        # from loss/zero to profit counts as growth; deeper loss is negative
        return 1.0 if last > first else -1.0
    return (last / first) ** (1 / years) - 1 if last > 0 else -1.0


def extract(ticker: str) -> dict:
    """Return the quality_universe row inputs for one ticker (metrics may be None)."""
    tk = yf.Ticker(ticker)
    info: dict = {}
    try:
        info = tk.info or {}
    except Exception as e:
        log.warning("%s: info failed: %s", ticker, e)

    try:
        income = tk.income_stmt
    except Exception:
        income = None
    try:
        balance = tk.balance_sheet
    except Exception:
        balance = None
    try:
        cashflow = tk.cashflow
    except Exception:
        cashflow = None

    roe = info.get("returnOnEquity")

    # D/E: info gives percent (e.g. 41.3); fall back to balance sheet.
    de = info.get("debtToEquity")
    de = de / 100.0 if isinstance(de, (int, float)) else None
    if de is None:
        debt = _row(balance, "Total Debt")
        equity = _row(balance, "Stockholders Equity", "Total Stockholder Equity")
        if debt is not None and equity is not None and float(equity.iloc[-1]) > 0:
            de = float(debt.iloc[-1]) / float(equity.iloc[-1])

    fcf = info.get("freeCashflow")
    if fcf is None:
        ocf = _row(cashflow, "Operating Cash Flow", "Total Cash From Operating Activities")
        capex = _row(cashflow, "Capital Expenditure", "Capital Expenditures")
        if ocf is not None and capex is not None:
            fcf = float(ocf.iloc[-1]) + float(capex.iloc[-1])  # capex reported negative

    # ROIC approx: EBIT * (1 - 21%) / (equity + total debt), latest year.
    roic = None
    ebit = _row(income, "EBIT", "Operating Income")
    equity_s = _row(balance, "Stockholders Equity", "Total Stockholder Equity")
    debt_s = _row(balance, "Total Debt")
    if ebit is not None and equity_s is not None:
        invested = float(equity_s.iloc[-1]) + (float(debt_s.iloc[-1]) if debt_s is not None else 0)
        if invested > 0:
            roic = float(ebit.iloc[-1]) * 0.79 / invested

    revenue = _row(income, "Total Revenue")
    eps = _row(income, "Diluted EPS", "Basic EPS")
    net_income = _row(income, "Net Income")
    rev_growth = _cagr(revenue)
    eps_growth = _cagr(eps) if eps is not None else _cagr(net_income)

    gm_avg = gm_stdev = gm_latest = None
    gross = _row(income, "Gross Profit")
    if gross is not None and revenue is not None:
        gm = (gross / revenue.reindex(gross.index)).dropna()
        if len(gm) >= 2:
            gm_avg = float(gm.mean())
            gm_stdev = float(gm.std())
            gm_latest = float(gm.iloc[-1])

    return _sanitize({
        "ticker": ticker,
        "name": info.get("shortName"),
        "roe": roe,
        "roic": roic,
        "debt_to_equity": de,
        "fcf": fcf,
        "rev_growth_3y": rev_growth,
        "eps_growth_3y": eps_growth,
        "gross_margin_avg": gm_avg,
        "gross_margin_stdev": gm_stdev,
        "raw": {
            "gross_margin_latest": gm_latest,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),
            "profit_margin": info.get("profitMargins"),
            "trailing_pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
        },
    })
