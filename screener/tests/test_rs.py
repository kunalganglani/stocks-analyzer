import numpy as np
import pytest

from screener.rs import build_breakpoints, percentile_of, rs_score

from conftest import make_df


def test_rs_score_matches_hand_computation():
    # Deterministic series: price doubles smoothly over 300 days.
    n = 300
    closes = 100 * (2 ** (np.arange(n) / (n - 1)))
    df = make_df(closes)
    s = rs_score(df["Close"])

    def r(w):
        return closes[-1] / closes[-1 - w] - 1.0

    expected = 0.4 * r(63) + 0.2 * r(126) + 0.2 * r(189) + 0.2 * r(252)
    assert s == pytest.approx(expected, rel=1e-9)


def test_rs_score_none_when_short_history():
    df = make_df(np.linspace(10, 20, 200))  # < 252+1 bars
    assert rs_score(df["Close"]) is None


def test_percentile_roundtrip():
    scores = list(np.linspace(-0.5, 2.0, 500))
    bp = build_breakpoints(scores)
    assert len(bp) == 101
    assert percentile_of(bp[0] - 1, bp) == 0.0
    assert percentile_of(bp[100] + 1, bp) == 100.0
    mid = percentile_of(float(np.percentile(scores, 70)), bp)
    assert 68 <= mid <= 72


def test_breakpoints_reject_tiny_sample():
    with pytest.raises(ValueError):
        build_breakpoints([0.1] * 5)
