"""Signal decision core: combines quality gate, trend template, VCP entry,
market regime, and sell rules into concrete signals.

BUY fires only when EVERY gate agrees ("multiple indicators shouting"):
  quality pass  AND  all-8 trend template  AND  VCP breakout  AND  risk-on regime
  AND no recent BUY for the ticker (cooldown).
Complete setup but risk-off regime -> WATCH (regime_blocked).
Setup tightening near the pivot -> WATCH (setup forming).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import pandas as pd

from . import rs as rs_mod
from . import sell_rules, trend_template, vcp
from .config import T
from .indicators import enrich
from .sizing import position_size


@dataclass
class Signal:
    ticker: str
    type: str                       # BUY | WATCH | SELL_* | CLIMAX_WARN
    price: float | None = None
    buy_point: float | None = None
    stop_price: float | None = None
    sizing: dict | None = None
    details: dict = field(default_factory=dict)
    position_id: int | None = None

    def to_row(self, signal_date: str) -> dict:
        d = asdict(self)
        d["signal_date"] = signal_date
        return d


def screen_ticker(ticker: str, df: pd.DataFrame, breakpoints: list[float] | None) -> dict:
    """Compute everything screenable for one ticker. Returns the daily_screens row."""
    e = enrich(df)
    last = e.iloc[-1]
    score = rs_mod.rs_score(e["Close"])
    rs_pct = (rs_mod.percentile_of(score, breakpoints)
              if score is not None and breakpoints else None)
    tt = trend_template.evaluate(e, rs_pct)
    v = vcp.detect(e) if tt["pass"] else {"status": "none", "pivot": None,
                                          "stop_candidate": None, "contractions": [],
                                          "dryup_ratio": None, "breakout_volume_ok": None}

    def f(x):
        return None if pd.isna(x) else float(x)

    return {
        "ticker": ticker,
        "close": f(last["Close"]),
        "ma50": f(last["ma50"]), "ma150": f(last["ma150"]), "ma200": f(last["ma200"]),
        "pct_above_52w_low": (None if pd.isna(last["low_52w"]) or last["low_52w"] <= 0
                              else round(float(last["Close"] / last["low_52w"] - 1), 4)),
        "pct_off_52w_high": (None if pd.isna(last["high_52w"]) or last["high_52w"] <= 0
                             else round(float(1 - last["Close"] / last["high_52w"]), 4)),
        "rs_score": None if score is None else round(score, 6),
        "rs_percentile": rs_pct,
        "tt_criteria": {k: v_ for k, v_ in tt.items() if k != "pass"},
        "tt_pass": tt["pass"],
        "vcp": v,
        "setup_status": v["status"],
        "_enriched": e,  # internal; stripped before DB write
    }


def buy_or_watch(row: dict, quality_pass: bool, risk_on: bool,
                 recent_buy: bool, settings: dict) -> Signal | None:
    """Apply the confluence gates to one screened ticker."""
    if not (quality_pass and row["tt_pass"]):
        return None
    status = row["setup_status"]
    v = row["vcp"]
    if status == "breakout" and not recent_buy:
        pivot = v["pivot"]
        stop_floor = pivot * (1 - T.max_stop_pct)
        stop = max(stop_floor, v["stop_candidate"] or stop_floor)
        stop = min(stop, pivot * 0.999)  # paranoia: stop strictly below buy point
        if risk_on:
            sz = position_size(settings["equity"], settings["risk_pct"],
                               settings["max_position_pct"], pivot, stop)
            return Signal(row["ticker"], "BUY", price=row["close"], buy_point=pivot,
                          stop_price=round(stop, 4), sizing=sz,
                          details={"vcp": _vcp_public(v), "tt": row["tt_criteria"]})
        return Signal(row["ticker"], "WATCH", price=row["close"], buy_point=pivot,
                      details={"reason": "regime_blocked", "vcp": _vcp_public(v)})
    if status == "pivot_near":
        return Signal(row["ticker"], "WATCH", price=row["close"], buy_point=v["pivot"],
                      details={"reason": "setup_forming", "vcp": _vcp_public(v)})
    return None


def position_signals(position: dict, df: pd.DataFrame | None) -> list[Signal]:
    if df is None or df.empty:
        s = sell_rules.no_data_signal(position)
        return [Signal(position["ticker"], s["type"], price=s["price"],
                       details=s["details"], position_id=position.get("id"))]
    e = enrich(df)
    return [Signal(position["ticker"], s["type"], price=s["price"], details=s["details"],
                   position_id=position.get("id"))
            for s in sell_rules.evaluate(e, position)]


def _vcp_public(v: dict) -> dict:
    return {k: v_ for k, v_ in v.items() if k != "_enriched"}
