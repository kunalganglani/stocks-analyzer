"""Shared test helpers: synthetic OHLCV builders.

Synthetic series let each test target one criterion precisely; frozen parquet
fixtures (tests/fixtures/) cover real-world shapes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def make_df(closes, volumes=None, highs=None, lows=None, start="2020-01-01") -> pd.DataFrame:
    """Build an OHLCV frame from close prices (business-day index)."""
    closes = np.asarray(closes, dtype=float)
    n = len(closes)
    idx = pd.bdate_range(start, periods=n)
    volumes = np.full(n, 1_000_000.0) if volumes is None else np.asarray(volumes, dtype=float)
    highs = closes * 1.01 if highs is None else np.asarray(highs, dtype=float)
    lows = closes * 0.99 if lows is None else np.asarray(lows, dtype=float)
    return pd.DataFrame(
        {"Open": closes, "High": highs, "Low": lows, "Close": closes, "Volume": volumes},
        index=idx,
    )


def steady_uptrend(n=400, start_price=20.0, daily=0.002) -> np.ndarray:
    """Monotonic geometric uptrend — passes every trend-template criterion."""
    return start_price * np.cumprod(np.full(n, 1 + daily))


@pytest.fixture
def uptrend_df():
    return make_df(steady_uptrend())
