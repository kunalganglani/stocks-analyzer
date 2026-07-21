"""Weekly job: liquid universe -> RS reference distribution -> quality universe.

  uv run python -m screener.jobs.run_weekly                 # full run
  uv run python -m screener.jobs.run_weekly --limit 25 --dry-run

Steps:
  1. Symbol lists from nasdaqtrader.com, junk filtered.
  2. Full-universe price download (chunked, cached) -> liquidity filter.
  3. RS scores for every liquid name -> 101 percentile breakpoints -> rs_reference.
  4. Fundamentals for stale tickers (>21 days old) -> quality gate -> quality_universe.

Resume is implicit: rerunning skips tickers checked within the staleness window.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import date, datetime, timezone

from .. import db, fundamentals, quality, universe
from ..config import T
from ..fetch import fetch_prices
from ..rs import build_breakpoints, rs_score

log = logging.getLogger("run_weekly")


def parse_args(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, help="cap number of fundamentals checks (testing)")
    p.add_argument("--tickers", help="comma list override (testing)")
    p.add_argument("--dry-run", action="store_true", help="no DB writes")
    p.add_argument("--throttle", type=float, default=0.6,
                   help="seconds to sleep between fundamentals calls")
    p.add_argument("--skip-fundamentals", action="store_true",
                   help="only refresh liquidity + RS reference")
    return p.parse_args(argv)


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = parse_args(argv)
    as_of = date.today().isoformat()
    dry = args.dry_run
    sb = None if dry else db.client()
    run_id = db.start_run(sb, as_of, "weekly") if sb else None

    try:
        if args.tickers:
            symbols = [t.strip().upper() for t in args.tickers.split(",")]
            names = {}
            exchanges = {}
        else:
            sym_df = universe.fetch_symbols()
            symbols = sym_df["ticker"].tolist()
            names = dict(zip(sym_df["ticker"], sym_df["name"]))
            exchanges = dict(zip(sym_df["ticker"], sym_df["exchange"]))
        log.info("symbol universe: %d", len(symbols))

        prices, missing = fetch_prices(symbols, as_of)
        log.info("prices fetched: %d ok, %d missing", len(prices), len(missing))

        liquid = universe.liquidity_filter(prices, T.min_price, T.min_avg_dollar_volume)
        log.info("liquid universe: %d", len(liquid))

        scores = []
        for t in liquid:
            s = rs_score(prices[t]["Close"])
            if s is not None:
                scores.append(s)
        breakpoints = build_breakpoints(scores)
        log.info("RS reference built from %d scores (p70=%.4f)", len(scores), breakpoints[70])
        if sb:
            db.store_rs_reference(sb, as_of, breakpoints)

        checked = passed = 0
        if not args.skip_fundamentals:
            targets = (db.stale_quality_tickers(sb, liquid, T.fundamentals_stale_days)
                       if sb else list(liquid))
            if args.limit:
                targets = targets[: args.limit]
            log.info("fundamentals to check: %d", len(targets))

            batch: list[dict] = []
            now = datetime.now(timezone.utc).isoformat()
            for i, t in enumerate(targets):
                try:
                    f = fundamentals.extract(t)
                except Exception as e:
                    log.warning("%s: fundamentals failed: %s", t, e)
                    continue
                ok, reasons = quality.evaluate(f)
                row = {**f, "passes": ok, "fail_reasons": reasons, "checked_at": now,
                       "exchange": exchanges.get(t)}
                row["name"] = row.get("name") or names.get(t)
                batch.append(row)
                checked += 1
                passed += int(ok)
                if sb and len(batch) >= 50:
                    db.upsert_quality(sb, batch)
                    batch = []
                if i % 100 == 0:
                    log.info("fundamentals progress %d/%d (%d pass)", i, len(targets), passed)
                time.sleep(args.throttle)
            if sb and batch:
                db.upsert_quality(sb, batch)
            if dry:
                for r in batch[:20]:
                    print(f"{r['ticker']:6} pass={r['passes']} {r['fail_reasons']}")

        stats = {"symbols": len(symbols), "priced": len(prices), "liquid": len(liquid),
                 "rs_scores": len(scores), "fundamentals_checked": checked,
                 "fundamentals_passed": passed}
        log.info("weekly stats: %s", stats)
        if sb:
            db.finish_run(sb, run_id, "ok", stats=stats)
            from ..alerts import send_weekly_summary
            send_weekly_summary(sb, as_of, stats)
        return 0
    except Exception as e:
        log.exception("weekly run failed")
        if sb and run_id:
            db.finish_run(sb, run_id, "failed", error=str(e))
            from ..alerts import send_failure
            send_failure("weekly", as_of, str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
