"""Risk-based position sizing: risk a fixed % of equity per trade,
capped at a max % of equity in any single position."""

from __future__ import annotations

import math


def position_size(equity: float, risk_pct: float, max_position_pct: float,
                  buy_point: float, stop_price: float) -> dict:
    risk_dollars = equity * risk_pct / 100.0
    stop_distance = buy_point - stop_price
    if stop_distance <= 0:
        return {"shares": 0, "reason": "stop above buy point"}
    shares = math.floor(risk_dollars / stop_distance)
    max_shares = math.floor(equity * max_position_pct / 100.0 / buy_point)
    shares = min(shares, max_shares)
    return {
        "equity": equity,
        "risk_pct": risk_pct,
        "risk_dollars": round(risk_dollars, 2),
        "stop_distance_pct": round(stop_distance / buy_point * 100, 2),
        "shares": shares,
        "position_value": round(shares * buy_point, 2),
        "capped_by_max_position": shares == max_shares,
    }
