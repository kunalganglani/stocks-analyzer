import numpy as np

from screener.indicators import enrich
from screener.sell_rules import evaluate, no_data_signal

from conftest import make_df, steady_uptrend


def types(signals):
    return {s["type"] for s in signals}


def pos(entry, stop=None):
    return {"ticker": "TEST", "entry_price": entry, "stop_price": stop, "shares": 10}


def test_stop_hit_on_intraday_low(uptrend_df):
    df = enrich(uptrend_df)
    entry = float(df["Close"].iloc[-1]) * 1.02
    # default stop = entry * 0.92; today's low ~ close*0.99 => close*0.99 <= entry*0.92?
    # Make it explicit instead: stop just above today's low.
    stop = float(df["Low"].iloc[-1]) + 0.01
    out = evaluate(df, pos(entry, stop))
    assert "SELL_STOP" in types(out)


def test_sell_strength_at_20pct(uptrend_df):
    df = enrich(uptrend_df)
    entry = float(df["Close"].iloc[-1]) / 1.25  # +25% gain
    out = evaluate(df, pos(entry))
    assert "SELL_STRENGTH" in types(out)


def test_trail_50d_needs_volume():
    up = steady_uptrend(400)
    up[-5:] = up[-6] * 0.93  # below ma50
    vols = np.full(400, 1_000_000.0)
    vols[-1] = 2_000_000.0  # above 50d avg volume
    df = enrich(make_df(up, volumes=vols))
    out = evaluate(df, pos(float(df["Close"].iloc[-1]) * 1.05))
    assert "SELL_TRAIL_50D" in types(out)

    vols[-1] = 500_000.0  # low volume: no trail signal
    df2 = enrich(make_df(up, volumes=vols))
    out2 = evaluate(df2, pos(float(df2["Close"].iloc[-1]) * 1.05))
    assert "SELL_TRAIL_50D" not in types(out2)


def test_hard_exit_below_200d():
    closes = np.concatenate([steady_uptrend(380), np.full(20, 10.0)])
    df = enrich(make_df(closes))
    out = evaluate(df, pos(50.0))
    assert "SELL_200D" in types(out)


def test_climax_warn_on_vertical_run():
    # Long steady uptrend, then +40% in 15 days => extended + climax.
    up = steady_uptrend(400, daily=0.003)
    up[-15:] = up[-16] * np.cumprod(np.full(15, 1.025))
    df = enrich(make_df(up))
    out = evaluate(df, pos(float(df["Close"].iloc[-1]) / 2))
    assert "CLIMAX_WARN" in types(out)


def test_quiet_uptrend_no_signals(uptrend_df):
    df = enrich(uptrend_df)
    entry = float(df["Close"].iloc[-1]) / 1.05  # +5% gain, stop far below
    out = evaluate(df, pos(entry, entry * 0.92))
    assert out == []


def test_no_data_position():
    s = no_data_signal({"ticker": "GONE"})
    assert "warning" in s["details"]


def test_empty_df_returns_no_data_signal():
    out = evaluate(make_df([]), pos(10.0))
    assert "warning" in out[0]["details"]
