"""IBD-style relative-strength score and percentile ranking.

Score = 0.4*r63 + 0.2*r126 + 0.2*r189 + 0.2*r252 (trailing trading-day returns,
recent quarter double-weighted). Percentile is looked up against a reference
distribution: 101 breakpoints (score at percentile 0..100) computed weekly over
the full liquid universe and stored in the DB.
"""

from __future__ import annotations

from bisect import bisect_right

import numpy as np
import pandas as pd

from .config import T
from .indicators import pct_return


def rs_score(close: pd.Series) -> float | None:
    """None if there isn't enough history for the longest window."""
    parts = []
    for w, wt in zip(T.rs_windows, T.rs_weights):
        r = pct_return(close, w)
        if r is None:
            return None
        parts.append(wt * r)
    return float(sum(parts))


def build_breakpoints(scores: list[float], min_n: int = 20) -> list[float]:
    """101 percentile breakpoints (p0..p100) of the universe score distribution.

    min_n guards live distributions; dry-run/backtest callers pass a lower bar.
    """
    arr = np.asarray([s for s in scores if s is not None and np.isfinite(s)])
    if arr.size < min_n:
        raise ValueError(f"too few RS scores to build a distribution: {arr.size}")
    return [float(np.percentile(arr, p)) for p in range(101)]


def percentile_of(score: float, breakpoints: list[float]) -> float:
    """Map a score onto 0..100 via the stored breakpoints (right-side rank)."""
    if len(breakpoints) != 101:
        raise ValueError("breakpoints must have 101 entries (p0..p100)")
    return float(min(100, bisect_right(breakpoints, score) - 1)) if score >= breakpoints[0] else 0.0
