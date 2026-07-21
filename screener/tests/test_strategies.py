from screener.strategies import evaluate_all, evaluate_buffett, evaluate_munger

GOOD = {
    "roe": 0.30, "roic": 0.20, "fcf": 1e9, "rev_growth_3y": 0.12, "eps_growth_3y": 0.15,
    "debt_to_equity": 0.4, "gross_margin_stdev": 0.01, "gross_margin_avg": 0.55,
    "raw": {"gross_margin_latest": 0.56},
}


def test_buffett_pass_and_fail():
    assert evaluate_buffett(GOOD)["pass"]
    bad = {**GOOD, "fcf": -5.0}
    r = evaluate_buffett(bad)
    assert not r["pass"] and not r["checks"]["positive_free_cash_flow"]


def test_buffett_missing_data_fails():
    r = evaluate_buffett(None)
    assert not r["pass"]
    assert not any(r["checks"].values())


def test_munger_debt_fail():
    r = evaluate_munger({**GOOD, "debt_to_equity": 8.0})
    assert not r["pass"] and not r["checks"]["low_debt"]


def test_munger_expanding_margins_ok():
    # volatile but expanding margins (the NVDA case) still passes
    r = evaluate_munger({**GOOD, "gross_margin_stdev": 0.09,
                         "raw": {"gross_margin_latest": 0.70}, "gross_margin_avg": 0.60})
    assert r["pass"]


def test_munger_no_gross_margin_tolerated():
    r = evaluate_munger({**GOOD, "gross_margin_stdev": None, "gross_margin_avg": None,
                         "raw": {}})
    assert r["checks"]["durable_margins"]


def test_evaluate_all_shape():
    tt = {"c1_price_above_150_200": True, "pass": True}
    out = evaluate_all(tt, GOOD)
    assert set(out) == {"minervini", "buffett", "munger"}
    assert out["minervini"]["pass"] and "c1_price_above_150_200" in out["minervini"]["checks"]
