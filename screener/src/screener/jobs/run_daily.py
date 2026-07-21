"""Daily screening job.

  uv run python -m screener.jobs.run_daily --tickers NVDA,MSFT --dry-run
  uv run python -m screener.jobs.run_daily --as-of 2024-03-01 --tickers NVDA,PYPL --dry-run
  uv run python -m screener.jobs.run_daily            # full run: DB + email

--dry-run: no DB, no email — prints signals. RS percentiles come from an
on-the-fly distribution over whatever tickers were loaded (documented
approximation; live runs use the stored weekly reference).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date

import pandas as pd

from .. import confluence, db, regime, strategies
from ..config import T
from ..fetch import fetch_prices
from ..indicators import enrich
from ..rs import build_breakpoints, rs_score

log = logging.getLogger("run_daily")

INDICES = ["SPY", "QQQ"]


def parse_args(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--tickers", help="comma list; default = quality universe from DB")
    p.add_argument("--as-of", default=date.today().isoformat(),
                   help="screen as of this date (YYYY-MM-DD); enables backtest mode")
    p.add_argument("--dry-run", action="store_true", help="no DB writes, no email")
    p.add_argument("--no-email", action="store_true", help="DB writes but no email")
    p.add_argument("--no-cache", action="store_true")
    return p.parse_args(argv)


def effective_screen_date(spy: pd.DataFrame, as_of: str) -> str | None:
    """If as_of has no market bar yet (evening before close, weekend, holiday),
    screen as of the latest completed trading day instead. None => data too old,
    something is wrong upstream."""
    last = spy.index[-1].date().isoformat()
    if last >= as_of:
        return as_of
    if (date.fromisoformat(as_of) - date.fromisoformat(last)).days > 5:
        return None
    return last


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = parse_args(argv)
    as_of = args.as_of
    dry = args.dry_run

    sb = None if dry else db.client()
    settings = (db.load_settings(sb) if sb else
                {"equity": T.equity, "risk_pct": T.risk_pct,
                 "max_position_pct": T.max_position_pct,
                 "regime_mode": "both", "email_policy": "on_change"})
    positions = db.open_positions(sb) if sb else []

    if args.tickers:
        candidates = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    elif sb:
        # Screen every analyzed ticker (pass or fail) so web strategy filters
        # have real data; the BUY gate still requires the full quality pass.
        candidates = db.checked_tickers(sb)
    else:
        candidates = []
    if not candidates and not positions:
        log.error("no candidates: pass --tickers or populate quality_universe first")
        return 2

    tickers = sorted(set(candidates) | {p["ticker"] for p in positions} | set(INDICES))
    log.info("fetching %d tickers as of %s", len(tickers), as_of)
    prices, missing = fetch_prices(tickers, as_of, use_cache=not args.no_cache)
    if missing:
        log.warning("missing price data: %s", ",".join(missing[:20]))

    if "SPY" not in prices or "QQQ" not in prices:
        log.error("index data unavailable — aborting")
        if sb:
            rid = db.start_run(sb, as_of, "daily")
            db.finish_run(sb, rid, "failed", error="index data unavailable")
        return 1

    spy = enrich(prices["SPY"])
    effective = effective_screen_date(prices["SPY"], as_of)
    if effective is None:
        log.error("latest SPY bar is >5 days old — data problem, aborting")
        if sb:
            rid = db.start_run(sb, as_of, "daily")
            db.finish_run(sb, rid, "failed", error="market data too old")
        return 1
    if effective != as_of:
        log.info("no market bar for %s yet — screening as of %s instead", as_of, effective)
        as_of = effective

    run_id = db.start_run(sb, as_of, "daily") if sb else None
    try:
        reg = regime.evaluate(spy, enrich(prices["QQQ"]), settings["regime_mode"])
        log.info("regime: risk_on=%s (spy>200d=%s qqq>200d=%s)",
                 reg["risk_on"], reg["spy"]["above_200"], reg["qqq"]["above_200"])

        # RS breakpoints: stored weekly reference, or on-the-fly for dry/backtest runs.
        breakpoints = db.latest_rs_breakpoints(sb) if sb else None
        if breakpoints is None:
            scores = [s for s in (rs_score(df["Close"]) for df in prices.values())
                      if s is not None]
            breakpoints = build_breakpoints(scores, min_n=5) if len(scores) >= 5 else None
            if breakpoints:
                log.info("using on-the-fly RS distribution over %d tickers", len(scores))

        # Screen position tickers too (even off-universe) so the dashboard always
        # has a fresh close/MA row for every held stock.
        screen_tickers = [t for t in sorted(set(candidates) | {p["ticker"] for p in positions})
                          if t in prices]
        rows = [confluence.screen_ticker(t, prices[t], breakpoints) for t in screen_tickers]

        fundamentals_by_ticker = db.quality_rows(sb) if sb else {}
        for row in rows:
            row["strategies"] = strategies.evaluate_all(
                {**row["tt_criteria"], "pass": row["tt_pass"]},
                fundamentals_by_ticker.get(row["ticker"]))

        quality = (set(db.quality_tickers(sb)) if sb
                   else set(screen_tickers) if args.tickers else set())
        recent_buys = (db.recent_buy_tickers(sb, as_of, T.buy_cooldown_days)
                       if sb else set())

        signals: list[confluence.Signal] = []
        for row in rows:
            sig = confluence.buy_or_watch(
                row, quality_pass=row["ticker"] in quality, risk_on=reg["risk_on"],
                recent_buy=row["ticker"] in recent_buys, settings=settings)
            if sig:
                signals.append(sig)

        for pos in positions:
            signals.extend(confluence.position_signals(pos, prices.get(pos["ticker"])))

        tt_passers = [r["ticker"] for r in rows if r["tt_pass"]]
        stats = {"tickers_requested": len(tickers), "fetched": len(prices),
                 "missing": len(missing), "tt_passers": len(tt_passers),
                 "signals": len(signals)}
        log.info("TT passers (%d): %s", len(tt_passers), ",".join(tt_passers[:30]))

        if dry:
            for s in signals:
                print(json.dumps(s.to_row(as_of), default=str, indent=2))
            print(f"\n== regime risk_on={reg['risk_on']}  stats={stats}")
            return 0

        db.store_strategy_meta(sb, strategies.META)
        db.upsert_screens(sb, as_of, rows)
        stored = db.upsert_signals(sb, as_of, signals)
        db.finish_run(sb, run_id, "ok", regime=reg, stats=stats)

        if not args.no_email:
            from ..alerts import send_digest
            send_digest(sb, as_of, stored, reg, settings)
        return 0
    except Exception as e:
        log.exception("daily run failed")
        if sb and run_id:
            db.finish_run(sb, run_id, "failed", error=str(e))
            from ..alerts import send_failure
            send_failure("daily", as_of, str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
