"""Supabase persistence. All writes are idempotent upserts so a rerun of the
same day's job cannot duplicate rows (unique constraints in the schema)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from supabase import Client, create_client

from . import config

log = logging.getLogger(__name__)


def client() -> Client:
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_KEY:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY not set")
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)


def load_settings(sb: Client) -> dict:
    rows = sb.table("settings").select("key,value").execute().data
    s = {r["key"]: r["value"] for r in rows}
    return {
        "equity": float(s.get("equity", config.T.equity)),
        "risk_pct": float(s.get("risk_pct", config.T.risk_pct)),
        "max_position_pct": float(s.get("max_position_pct", config.T.max_position_pct)),
        "regime_mode": s.get("regime_mode", "both"),
        "email_policy": s.get("email_policy", "on_change"),
    }


def open_positions(sb: Client) -> list[dict]:
    return sb.table("positions").select("*").eq("status", "open").execute().data


def quality_tickers(sb: Client) -> list[str]:
    rows = sb.table("quality_universe").select("ticker").eq("passes", True).execute().data
    return [r["ticker"] for r in rows]


def checked_tickers(sb: Client) -> list[str]:
    """Every ticker with analyzed fundamentals — pass or fail. The daily screen
    covers all of them so strategy filters on the web have real data."""
    out: list[str] = []
    page = 0
    while True:
        rows = (sb.table("quality_universe").select("ticker")
                .order("ticker").range(page * 1000, page * 1000 + 999).execute().data)
        out.extend(r["ticker"] for r in rows)
        if len(rows) < 1000:
            return out
        page += 1


def quality_rows(sb: Client) -> dict[str, dict]:
    """ticker -> fundamentals row (metrics + raw) for strategy evaluation."""
    out: dict[str, dict] = {}
    page = 0
    while True:
        rows = (sb.table("quality_universe").select("*")
                .order("ticker").range(page * 1000, page * 1000 + 999).execute().data)
        for r in rows:
            out[r["ticker"]] = r
        if len(rows) < 1000:
            return out
        page += 1


def store_strategy_meta(sb: Client, meta: list[dict]) -> None:
    sb.table("settings").upsert(
        {"key": "strategies", "value": meta}, on_conflict="key").execute()


def latest_rs_breakpoints(sb: Client) -> list[float] | None:
    rows = (sb.table("rs_reference").select("as_of,breakpoints")
            .order("as_of", desc=True).limit(1).execute().data)
    return rows[0]["breakpoints"] if rows else None


def recent_buy_tickers(sb: Client, signal_date: str, cooldown_days: int) -> set[str]:
    """Tickers with a BUY in the last ~cooldown_days trading days (calendar approx)."""
    from datetime import date, timedelta

    cutoff = (date.fromisoformat(signal_date) - timedelta(days=int(cooldown_days * 1.5)))
    rows = (sb.table("signals").select("ticker").eq("type", "BUY")
            .gte("signal_date", cutoff.isoformat()).execute().data)
    return {r["ticker"] for r in rows}


def upsert_screens(sb: Client, screen_date: str, rows: list[dict]) -> None:
    payload = []
    for r in rows:
        r = {k: v for k, v in r.items() if not k.startswith("_")}
        r["screen_date"] = screen_date
        payload.append(r)
    for i in range(0, len(payload), 500):
        sb.table("daily_screens").upsert(
            payload[i : i + 500], on_conflict="screen_date,ticker").execute()


def upsert_signals(sb: Client, signal_date: str, signals: list) -> list[dict]:
    """Upsert and return the stored rows (with emailed_at state)."""
    if not signals:
        return []
    payload = [s.to_row(signal_date) for s in signals]
    sb.table("signals").upsert(payload, on_conflict="signal_date,ticker,type").execute()
    return (sb.table("signals").select("*").eq("signal_date", signal_date).execute().data)


def mark_emailed(sb: Client, signal_ids: list[int]) -> None:
    if not signal_ids:
        return
    now = datetime.now(timezone.utc).isoformat()
    sb.table("signals").update({"emailed_at": now}).in_("id", signal_ids).execute()


def start_run(sb: Client, run_date: str, kind: str) -> int:
    row = sb.table("runs").insert({"run_date": run_date, "kind": kind}).execute().data[0]
    return row["id"]


def finish_run(sb: Client, run_id: int, status: str, regime: dict | None = None,
               stats: dict | None = None, error: str | None = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    sb.table("runs").update({"status": status, "regime": regime, "stats": stats,
                             "error": error, "finished_at": now}).eq("id", run_id).execute()


def upsert_quality(sb: Client, rows: list[dict]) -> None:
    for i in range(0, len(rows), 200):
        sb.table("quality_universe").upsert(rows[i : i + 200], on_conflict="ticker").execute()


def store_rs_reference(sb: Client, as_of: str, breakpoints: list[float]) -> None:
    sb.table("rs_reference").upsert(
        {"as_of": as_of, "breakpoints": breakpoints}, on_conflict="as_of").execute()


def stale_quality_tickers(sb: Client, all_tickers: list[str], stale_days: int) -> list[str]:
    """Tickers never checked or checked longer than stale_days ago."""
    from datetime import date, timedelta

    cutoff = (date.today() - timedelta(days=stale_days)).isoformat()
    rows = sb.table("quality_universe").select("ticker,checked_at").execute().data
    fresh = {r["ticker"] for r in rows if (r["checked_at"] or "")[:10] >= cutoff}
    return [t for t in all_tickers if t not in fresh]
