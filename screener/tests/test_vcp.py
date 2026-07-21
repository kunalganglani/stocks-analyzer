"""VCP detection on hand-built bases: tightening contractions + dry-up + breakout."""

import numpy as np

from screener.config import T
from screener.indicators import enrich
from screener.vcp import detect

from conftest import make_df, steady_uptrend


def build_vcp_series(breakout=False, breakout_volume=True, dryup=True):
    """Uptrend then a 3-contraction base (12%, 7%, 4%) around price 100."""
    lead = steady_uptrend(300, start_price=40.0, daily=0.0031)  # ends near 100
    p = lead[-1]

    def leg(frm, to, days):
        return np.linspace(frm, to, days)

    base = np.concatenate([
        leg(p, p * 0.88, 8), leg(p * 0.88, p, 9),          # -12% and recover
        leg(p, p * 0.93, 7), leg(p * 0.93, p * 0.995, 8),  # -7%
        leg(p * 0.995, p * 0.96, 6), leg(p * 0.96, p * 0.99, 10),  # -4%, tighten near pivot
    ])
    closes = np.concatenate([lead, base])
    n = len(closes)
    vols = np.full(n, 1_000_000.0)
    if dryup:
        vols[-12:] = 600_000.0  # volume dries up in the final contraction
    if breakout:
        closes = np.append(closes, closes[-300:].max() * 1.02)  # close above pivot
        vols = np.append(vols, 1_600_000.0 if breakout_volume else 900_000.0)
    return make_df(closes, volumes=vols)


def test_base_detected_near_pivot():
    r = detect(enrich(build_vcp_series()))
    assert r["status"] in ("pivot_near", "base_forming")
    assert r["pivot"] is not None
    assert len(r["contractions"]) >= T.vcp_min_contractions
    depths = [c["depth"] for c in r["contractions"]]
    assert all(b <= a * T.vcp_step_tolerance for a, b in zip(depths, depths[1:]))
    assert depths[-1] <= depths[0] * T.vcp_contraction_decay


def test_breakout_with_volume():
    r = detect(enrich(build_vcp_series(breakout=True)))
    assert r["status"] == "breakout"
    assert r["breakout_volume_ok"]


def test_breakout_without_volume_is_not_a_buy():
    r = detect(enrich(build_vcp_series(breakout=True, breakout_volume=False)))
    assert r["status"] != "breakout"


def test_no_pattern_on_plain_uptrend(uptrend_df):
    r = detect(enrich(uptrend_df))
    assert r["status"] in ("none", "base_forming")  # never a breakout without a base
    assert r["status"] != "breakout"


def test_short_history_returns_none():
    r = detect(enrich(make_df(np.linspace(10, 20, 30))))
    assert r["status"] == "none"
