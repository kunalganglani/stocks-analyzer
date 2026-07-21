"""Basic indicator computations on a single-ticker OHLCV DataFrame.

Convention everywhere in this package: `df` is a pandas DataFrame with columns
Open/High/Low/Close/Volume and an ascending DatetimeIndex of daily bars.
All functions are pure — no I/O.
"""

from __future__ import annotations

import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window, min_periods=window).mean()


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with the derived columns the rest of the package expects."""
    out = df.copy()
    close = out["Close"]
    out["ma50"] = sma(close, 50)
    out["ma150"] = sma(close, 150)
    out["ma200"] = sma(close, 200)
    out["vol50"] = sma(out["Volume"], 50)
    out["vol10"] = sma(out["Volume"], 10)
    out["low_52w"] = close.rolling(252, min_periods=100).min()
    out["high_52w"] = close.rolling(252, min_periods=100).max()
    return out


def pct_return(close: pd.Series, window: int) -> float | None:
    """Simple % return over the trailing `window` trading days, None if not enough data."""
    if len(close) <= window:
        return None
    past = close.iloc[-window - 1]
    if past <= 0:
        return None
    return float(close.iloc[-1] / past - 1.0)


def avg_dollar_volume(df: pd.DataFrame, window: int = 50) -> float | None:
    if len(df) < window:
        return None
    dv = (df["Close"] * df["Volume"]).rolling(window).mean()
    val = dv.iloc[-1]
    return None if pd.isna(val) else float(val)
