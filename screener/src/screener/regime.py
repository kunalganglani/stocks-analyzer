"""Market regime gate — don't fight the tape.

Risk-on only when the index closes above its 200-day MA. `mode` (DB setting):
  both     - SPY and QQQ must both be above (default, most conservative)
  either   - one of them is enough
  spy_only - SPY decides
"""

from __future__ import annotations

import pandas as pd


def index_state(df: pd.DataFrame) -> dict:
    last = df.iloc[-1]
    above = bool(not pd.isna(last["ma200"]) and last["Close"] > last["ma200"])
    return {"close": float(last["Close"]),
            "ma200": None if pd.isna(last["ma200"]) else float(last["ma200"]),
            "above_200": above}


def evaluate(spy: pd.DataFrame, qqq: pd.DataFrame, mode: str = "both") -> dict:
    s, q = index_state(spy), index_state(qqq)
    if mode == "spy_only":
        risk_on = s["above_200"]
    elif mode == "either":
        risk_on = s["above_200"] or q["above_200"]
    else:
        risk_on = s["above_200"] and q["above_200"]
    return {"spy": s, "qqq": q, "mode": mode, "risk_on": bool(risk_on)}
