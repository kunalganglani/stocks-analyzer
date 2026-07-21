from screener.fundamentals import _sanitize


def test_sanitize_replaces_non_finite():
    row = {"roe": float("inf"), "fcf": float("nan"), "ok": 1.5,
           "raw": {"pe": float("-inf"), "sector": "Tech", "list": [1.0, float("inf")]}}
    out = _sanitize(row)
    assert out["roe"] is None and out["fcf"] is None and out["ok"] == 1.5
    assert out["raw"]["pe"] is None and out["raw"]["sector"] == "Tech"
    assert out["raw"]["list"] == [1.0, None]
