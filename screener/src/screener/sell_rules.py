"""Per-position sell rules (Minervini risk management). Regime-independent —
positions are protected in every market.

Input: enrich()-ed DataFrame for the ticker + the position dict
(entry_price, stop_price, shares). Output: list of signal dicts.
"""

from __future__ import annotations

import pandas as pd

from .config import T


def evaluate(df: pd.DataFrame, position: dict) -> list[dict]:
    signals: list[dict] = []
    if df is None or df.empty:
        return [no_data_signal(position)]

    last = df.iloc[-1]
    close = float(last["Close"])
    entry = float(position["entry_price"])
    stop = float(position.get("stop_price") or entry * (1 - T.max_stop_pct))
    gain = close / entry - 1.0

    def sig(type_: str, **details) -> dict:
        return {"type": type_, "price": close,
                "details": {"entry": entry, "gain_pct": round(gain * 100, 2), **details}}

    # 1. Hard stop — intraday low touched the stop.
    if float(last["Low"]) <= stop:
        signals.append(sig("SELL_STOP", stop=round(stop, 4), day_low=float(last["Low"])))

    # 2. Sell into strength at +20% (dedup handled by unique signal constraint upstream).
    if gain >= T.sell_strength_gain:
        signals.append(sig("SELL_STRENGTH", threshold_pct=T.sell_strength_gain * 100))

    # 3. Trend break: close below 50d MA on above-average volume.
    if (not pd.isna(last["ma50"]) and not pd.isna(last["vol50"])
            and close < float(last["ma50"]) and float(last["Volume"]) > float(last["vol50"])):
        signals.append(sig("SELL_TRAIL_50D", ma50=float(last["ma50"])))

    # 4. Hard exit: close below 200d MA.
    if not pd.isna(last["ma200"]) and close < float(last["ma200"]):
        signals.append(sig("SELL_200D", ma200=float(last["ma200"])))

    # 5. Climax run: huge gain in a short window while far extended above the 200d.
    if len(df) > T.climax_window and not pd.isna(last["ma200"]):
        recent_gain = close / float(df["Close"].iloc[-1 - T.climax_window]) - 1.0
        extended = close >= T.climax_extension_vs_ma200 * float(last["ma200"])
        if recent_gain >= T.climax_gain and extended:
            signals.append(sig("CLIMAX_WARN",
                               recent_gain_pct=round(recent_gain * 100, 2),
                               window_days=T.climax_window))
    return signals


def no_data_signal(position: dict) -> dict:
    """Held ticker with no price data (delisted/renamed) — surface it, don't crash."""
    return {"type": "SELL_200D", "price": None,
            "details": {"warning": "no price data for held position "
                                   f"{position['ticker']} — check for delisting/rename"}}
