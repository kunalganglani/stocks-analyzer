"""Minervini's 8-criteria Trend Template.

Input: an `indicators.enrich()`-ed DataFrame plus the ticker's RS percentile
(computed separately against the universe distribution). Output: per-criterion
booleans and the overall pass flag. A ticker with insufficient history
(< 200 bars for the MAs) fails rather than passes.
"""

from __future__ import annotations

import pandas as pd

from .config import T


def evaluate(df: pd.DataFrame, rs_percentile: float | None) -> dict:
    last = df.iloc[-1]
    close, ma50, ma150, ma200 = last["Close"], last["ma50"], last["ma150"], last["ma200"]
    low52, high52 = last["low_52w"], last["high_52w"]

    have_mas = not any(pd.isna(x) for x in (ma50, ma150, ma200, low52, high52))

    lb = T.ma200_rising_lookback
    ma200_rising = (
        have_mas
        and len(df) > 200 + lb
        and not pd.isna(df["ma200"].iloc[-1 - lb])
        and df["ma200"].iloc[-1] > df["ma200"].iloc[-1 - lb]
    )

    c = {
        "c1_price_above_150_200": bool(have_mas and close > ma150 and close > ma200),
        "c2_ma150_above_200": bool(have_mas and ma150 > ma200),
        "c3_ma200_rising_1m": bool(ma200_rising),
        "c4_ma50_above_150_200": bool(have_mas and ma50 > ma150 and ma50 > ma200),
        "c5_price_above_50": bool(have_mas and close > ma50),
        "c6_above_52w_low_30pct": bool(
            have_mas and low52 > 0 and close >= low52 * (1 + T.min_pct_above_52w_low)
        ),
        "c7_within_25pct_of_high": bool(
            have_mas and high52 > 0 and close >= high52 * (1 - T.max_pct_off_52w_high)
        ),
        "c8_rs_ge_70": bool(rs_percentile is not None and rs_percentile >= T.rs_min_percentile),
    }
    c["pass"] = all(c.values())
    return c
