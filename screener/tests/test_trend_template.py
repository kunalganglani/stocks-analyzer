"""One targeted failing case per Trend Template criterion, plus the all-pass case."""

import numpy as np

from screener.indicators import enrich
from screener.trend_template import evaluate

from conftest import make_df, steady_uptrend


def ev(closes, rs=90.0, **kw):
    return evaluate(enrich(make_df(closes, **kw)), rs_percentile=rs)


def test_all_pass_on_steady_uptrend(uptrend_df):
    c = evaluate(enrich(uptrend_df), rs_percentile=90.0)
    assert c["pass"], c


def test_c1_fails_below_long_mas():
    # Long uptrend then a crash below both long MAs.
    closes = np.concatenate([steady_uptrend(380), np.full(20, 10.0)])
    c = ev(closes)
    assert not c["c1_price_above_150_200"] and not c["pass"]


def test_c2_fails_when_150_below_200():
    # Long decline: ma150 sits below ma200.
    closes = 100 * np.cumprod(np.full(400, 1 - 0.002))
    c = ev(closes)
    assert not c["c2_ma150_above_200"] and not c["pass"]


def test_c3_fails_when_ma200_flat():
    # Perfectly flat series: 200d MA not rising.
    c = ev(np.full(400, 50.0))
    assert not c["c3_ma200_rising_1m"] and not c["pass"]


def test_c4_fails_when_50_below_150():
    # Uptrend that stalls and slides for ~3 months: ma50 dips below ma150.
    closes = np.concatenate([steady_uptrend(340),
                             steady_uptrend(340)[-1] * np.cumprod(np.full(60, 0.997))])
    c = ev(closes)
    assert not c["c4_ma50_above_150_200"] and not c["pass"]


def test_c5_fails_price_below_50d():
    # Sharp 12-day dip: price below ma50 while long MAs still fine.
    up = steady_uptrend(400)
    up[-12:] = up[-13] * 0.90
    c = ev(up)
    assert not c["c5_price_above_50"] and not c["pass"]


def test_c6_fails_too_close_to_52w_low():
    # Grinding sideways just above its 52w low (< 30% above).
    base = np.linspace(100, 110, 400)  # only 10% off the low
    c = ev(base)
    assert not c["c6_above_52w_low_30pct"] and not c["pass"]


def test_c7_fails_too_far_from_high():
    # Big run-up then a 40% drawdown — far below the 52w high.
    up = steady_uptrend(340, daily=0.004)
    closes = np.concatenate([up, np.full(60, up[-1] * 0.60)])
    c = ev(closes)
    assert not c["c7_within_25pct_of_high"] and not c["pass"]


def test_c8_fails_low_rs(uptrend_df):
    c = evaluate(enrich(uptrend_df), rs_percentile=55.0)
    assert not c["c8_rs_ge_70"] and not c["pass"]


def test_c8_fails_missing_rs(uptrend_df):
    c = evaluate(enrich(uptrend_df), rs_percentile=None)
    assert not c["c8_rs_ge_70"] and not c["pass"]


def test_insufficient_history_fails():
    c = ev(steady_uptrend(120))  # < 200 bars: no ma200
    assert not c["pass"]
