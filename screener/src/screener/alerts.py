"""Email alerts via the Resend HTTP API.

Policy ("on_change"): the daily job emails ONLY when something actionable
happened — a new BUY, any SELL/CLIMAX on a held position, a regime flip, or a
new WATCH (setup near pivot). Quiet days write to the DB only. The weekly job
always sends a Sunday summary. `signals.emailed_at` guards against duplicates
across reruns of the same day.
"""

from __future__ import annotations

import logging

import httpx

from . import config, db

log = logging.getLogger(__name__)

SELL_TYPES = ("SELL_STOP", "SELL_STRENGTH", "SELL_TRAIL_50D", "SELL_200D", "CLIMAX_WARN")

SELL_ADVICE = {
    "SELL_STOP": "Stop-loss hit — exit the position. Protecting capital is rule #1.",
    "SELL_STRENGTH": "Up 20%+ — consider selling into strength (at least partial).",
    "SELL_TRAIL_50D": "Closed below the 50-day MA on above-average volume — trend is weakening.",
    "SELL_200D": "Closed below the 200-day MA — hard exit signal.",
    "CLIMAX_WARN": "Climax-run behavior: vertical gains while extended. Consider locking in profit.",
}


def _post_email(subject: str, html: str) -> bool:
    if not config.RESEND_API_KEY:
        log.warning("RESEND_API_KEY not set — skipping email '%s'", subject)
        return False
    r = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {config.RESEND_API_KEY}"},
        json={"from": config.ALERT_FROM, "to": [config.ALERT_TO],
              "subject": subject, "html": html},
        timeout=30,
    )
    if r.status_code >= 300:
        log.error("resend failed %s: %s", r.status_code, r.text[:300])
        return False
    return True


def _fmt_money(x) -> str:
    return "—" if x is None else f"${float(x):,.2f}"


def _sig_block(title: str, rows: list[str]) -> str:
    if not rows:
        return ""
    return f"<h3 style='margin:16px 0 6px'>{title}</h3>" + "".join(rows)


def _regime_flipped(sb, as_of: str, current_risk_on: bool) -> bool:
    rows = (sb.table("runs").select("run_date,regime").eq("kind", "daily")
            .eq("status", "ok").lt("run_date", as_of)
            .order("run_date", desc=True).limit(1).execute().data)
    if not rows or not rows[0].get("regime"):
        return False
    return bool(rows[0]["regime"].get("risk_on")) != current_risk_on


def send_digest(sb, as_of: str, stored_signals: list[dict], regime: dict,
                settings: dict) -> None:
    unsent = [s for s in stored_signals if not s.get("emailed_at")]
    buys = [s for s in unsent if s["type"] == "BUY"]
    sells = [s for s in unsent if s["type"] in SELL_TYPES]
    watches = [s for s in unsent if s["type"] == "WATCH"]
    flipped = _regime_flipped(sb, as_of, regime["risk_on"])

    if not (buys or sells or watches or flipped):
        log.info("nothing new — no email today")
        return

    sell_rows = [
        f"<p><b>{s['ticker']}</b> — {s['type']} at {_fmt_money(s['price'])}<br>"
        f"<i>{SELL_ADVICE.get(s['type'], '')}</i></p>"
        for s in sells
    ]
    buy_rows = []
    for s in buys:
        sz = s.get("sizing") or {}
        buy_rows.append(
            f"<p><b>{s['ticker']}</b> — BUY point {_fmt_money(s['buy_point'])}, "
            f"last {_fmt_money(s['price'])}<br>"
            f"Stop: {_fmt_money(s['stop_price'])} "
            f"({sz.get('stop_distance_pct', '—')}% risk) · "
            f"Size: {sz.get('shares', '—')} shares (~{_fmt_money(sz.get('position_value'))})<br>"
            f"<i>All gates aligned: quality + trend template + VCP breakout + risk-on market.</i></p>"
        )
    watch_rows = [
        f"<p><b>{s['ticker']}</b> — setup near pivot {_fmt_money(s['buy_point'])} "
        f"({(s.get('details') or {}).get('reason', '')})</p>"
        for s in watches
    ]

    reg_line = ("RISK-ON — SPY & QQQ above 200d" if regime["risk_on"]
                else "RISK-OFF — buys suppressed")
    if flipped:
        reg_line = f"<b>REGIME FLIP:</b> now {reg_line}"

    if sells:
        subject = f"SELL signal: {', '.join(s['ticker'] for s in sells)} — {as_of}"
    elif buys:
        subject = f"BUY signal: {', '.join(s['ticker'] for s in buys)} — {as_of}"
    elif flipped:
        subject = f"Market regime flip — {as_of}"
    else:
        subject = f"Watchlist: setups forming — {as_of}"

    html = (
        f"<div style='font-family:sans-serif;max-width:560px'>"
        f"<p style='color:#555'>{reg_line}</p>"
        + _sig_block("Sell / protect positions", sell_rows)
        + _sig_block("Buy signals", buy_rows)
        + _sig_block("Watchlist", watch_rows)
        + "<hr><p style='color:#999;font-size:12px'>stocks-analyzer · signals are "
          "end-of-day · verify the chart before acting</p></div>"
    )
    if _post_email(subject, html):
        db.mark_emailed(sb, [s["id"] for s in unsent])
        log.info("digest sent: %s", subject)


def send_weekly_summary(sb, as_of: str, stats: dict) -> None:
    q = sb.table("quality_universe").select("ticker").eq("passes", True).execute().data
    positions = db.open_positions(sb)
    pos_rows = "".join(
        f"<li>{p['ticker']} — {p['shares']} @ {_fmt_money(p['entry_price'])}</li>"
        for p in positions) or "<li>none</li>"
    html = (
        f"<div style='font-family:sans-serif;max-width:560px'>"
        f"<h3>Weekly summary — {as_of}</h3>"
        f"<p>Liquid universe: {stats.get('liquid')} · quality passers: {len(q)} · "
        f"fundamentals checked this run: {stats.get('fundamentals_checked')}</p>"
        f"<p>Open positions:</p><ul>{pos_rows}</ul>"
        f"</div>"
    )
    _post_email(f"Weekly summary — {as_of}", html)


def send_failure(kind: str, as_of: str, error: str) -> None:
    _post_email(f"stocks-analyzer {kind} run FAILED — {as_of}",
                f"<pre>{error[:2000]}</pre>")
