"""Volatility Contraction Pattern (VCP) detection — the entry trigger.

Approximation of Minervini's VCP on daily bars:
  1. Find swing highs/lows over the base window (rolling extrema).
  2. Contractions = successive pullback depths (swing high -> subsequent swing low).
     Require >= 2, each depth <= decay * previous, final contraction shallow.
  3. Volume dry-up in the final contraction (10d avg < ratio * 50d avg).
  4. Breakout: close above pivot (final contraction's high) on >= 1.4x 50d volume,
     but not extended more than 5% past the pivot (no chasing).

Deliberately conservative: this is the LAST gate after quality + trend template +
regime, and a missed signal is acceptable where a bad one is not.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import T


def _swing_points(base: pd.DataFrame, window: int) -> tuple[list[int], list[int]]:
    """Indices (positional, within `base`) of swing highs and lows.

    A swing high is a bar whose High is the max of the +/- `window` neighborhood;
    swing lows analogous on Low.
    """
    highs, lows = [], []
    h, low = base["High"].to_numpy(), base["Low"].to_numpy()
    n = len(base)
    for i in range(window, n - window):
        seg_h = h[i - window : i + window + 1]
        seg_l = low[i - window : i + window + 1]
        if h[i] == seg_h.max():
            highs.append(i)
        if low[i] == seg_l.min():
            lows.append(i)
    return highs, lows


def _contractions(base: pd.DataFrame, highs: list[int], lows: list[int]) -> list[dict]:
    """Pair each swing high with the deepest subsequent low before the next swing high."""
    out = []
    h = base["High"].to_numpy()
    low = base["Low"].to_numpy()
    for k, hi in enumerate(highs):
        nxt = highs[k + 1] if k + 1 < len(highs) else len(base)
        seg_lows = [j for j in lows if hi < j < nxt]
        if not seg_lows:
            continue
        j = min(seg_lows, key=lambda idx: low[idx])
        depth = float(1.0 - low[j] / h[hi]) if h[hi] > 0 else 0.0
        out.append({"high_idx": hi, "low_idx": j, "high": float(h[hi]),
                    "low": float(low[j]), "depth": round(depth, 4)})
    return out


def detect(df: pd.DataFrame) -> dict:
    """Evaluate the VCP state as of the last bar of an enrich()-ed DataFrame.

    Returns {status, pivot, stop_candidate, contractions, dryup_ratio, breakout_volume_ok}.
    status: none | base_forming | pivot_near | breakout
    """
    result = {"status": "none", "pivot": None, "stop_candidate": None,
              "contractions": [], "dryup_ratio": None, "breakout_volume_ok": None}
    if len(df) < T.vcp_lookback + T.vcp_swing_window:
        return result

    base = df.iloc[-T.vcp_lookback :]
    highs, lows = _swing_points(base, T.vcp_swing_window)
    contractions = _contractions(base, highs, lows)
    if len(contractions) < T.vcp_min_contractions:
        return result

    # Trailing run of non-expanding contractions (adjacent plateaus tolerated),
    # then require overall tightening: final <= decay * first.
    run = [contractions[0]]
    for c in contractions[1:]:
        if c["depth"] <= run[-1]["depth"] * T.vcp_step_tolerance:
            run.append(c)
        else:
            run = [c]  # volatility expanded — restart the run here
    result["contractions"] = run
    if len(run) < T.vcp_min_contractions:
        result["status"] = "none"
        return result

    final = run[-1]
    if (final["depth"] > T.vcp_max_final_contraction
            or final["depth"] > run[0]["depth"] * T.vcp_contraction_decay):
        return result

    pivot = final["high"]
    result["pivot"] = round(pivot, 4)
    result["stop_candidate"] = round(final["low"], 4)

    last = df.iloc[-1]
    close, vol = float(last["Close"]), float(last["Volume"])
    vol50, vol10 = last["vol50"], last["vol10"]
    if pd.isna(vol50) or pd.isna(vol10) or vol50 <= 0:
        return result

    dryup = float(vol10 / vol50)
    result["dryup_ratio"] = round(dryup, 3)
    dryup_ok = dryup < T.vcp_dryup_ratio

    breakout_vol_ok = vol >= T.vcp_breakout_volume_mult * float(vol50)
    result["breakout_volume_ok"] = bool(breakout_vol_ok)

    if close > pivot:
        if close > pivot * (1 + T.vcp_max_extension):
            result["status"] = "base_forming"  # too extended to chase
        elif breakout_vol_ok:
            result["status"] = "breakout"
        else:
            # crossed the pivot on quiet volume — worth watching, not buying
            result["status"] = "pivot_near"
    elif close >= pivot * (1 - T.vcp_pivot_near_pct) and dryup_ok:
        result["status"] = "pivot_near"
    else:
        result["status"] = "base_forming"
    return result


def np_float(x) -> float | None:
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else float(x)
