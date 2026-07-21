import { Badge } from "@/components/badge";
import { EmptyState } from "@/components/empty-state";
import { Row, Section } from "@/components/section-card";
import { TickerLink } from "@/components/ticker-link";
import { fmtDate, isScreenStale, money } from "@/lib/format";
import { regimeCopy, SETUP_META, signalMeta, WATCH_REASON } from "@/lib/labels";
import {
  latestRun,
  latestScreenDate,
  openPositions,
  qualityCount,
  recentSignals,
  safe,
  screenRows,
} from "@/lib/queries";
import { RunNowButton } from "./run-now";

export const dynamic = "force-dynamic";

export default async function Dashboard() {
  const [run, date, positions, quality] = await Promise.all([
    safe(() => latestRun(), null),
    safe(() => latestScreenDate(), null),
    safe(() => openPositions(), []),
    safe(() => qualityCount(), 0),
  ]);
  const signals = (await safe(() => recentSignals(7), [])).filter(
    (s) => s.signal_date === (date ?? "")
  );
  const screens = date ? await safe(() => screenRows(date), []) : [];
  const setups = screens.filter(
    (r) => r.setup_status === "pivot_near" || r.setup_status === "breakout"
  );

  const regime = run?.regime as { risk_on?: boolean } | null;
  const reg = regimeCopy(regime?.risk_on);

  const buys = signals.filter((s) => s.type === "BUY");
  const sells = signals.filter((s) => s.type.startsWith("SELL") || s.type === "CLIMAX_WARN");
  const watches = signals.filter((s) => s.type === "WATCH");

  const stale = isScreenStale(date) || run?.status === "failed";

  // The 3-second answer: what should I do today?
  let verdict: { text: string; cls: string };
  if (sells.length > 0) {
    verdict = {
      text: `${sells.length} position${sells.length > 1 ? "s" : ""} need${sells.length > 1 ? "" : "s"} attention`,
      cls: "text-red-600 dark:text-red-400",
    };
  } else if (buys.length > 0) {
    verdict = {
      text: `${buys.length} BUY signal${buys.length > 1 ? "s" : ""} today`,
      cls: "text-emerald-600 dark:text-emerald-400",
    };
  } else if (watches.length > 0 || setups.length > 0) {
    const n = Math.max(watches.length, setups.length);
    verdict = { text: `Nothing to buy yet — ${n} setup${n > 1 ? "s" : ""} forming`, cls: "" };
  } else {
    verdict = { text: "Nothing to do today", cls: "" };
  }

  return (
    <main className="space-y-8 py-8">
      <section className="space-y-3">
        <h1 className={`text-3xl font-semibold ${verdict.cls}`}>{verdict.text}</h1>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <Badge tone={reg.tone} title={reg.explain}>
            {reg.label}
          </Badge>
          {stale ? (
            <Badge tone="warn" title="The nightly screen hasn't reported recently — press Run screener now to refresh.">
              screened {fmtDate(date)} — may be out of date
            </Badge>
          ) : (
            <span className="text-faint">screened {fmtDate(date)}</span>
          )}
          <span className="text-faint">· watching {quality} quality stocks</span>
          <RunNowButton />
        </div>
      </section>

      {sells.length > 0 && (
        <Section title="⚠ Protect your positions" tone="red">
          {sells.map((s) => {
            const m = signalMeta(s.type);
            return (
              <Row key={s.id}>
                <div className="flex flex-wrap items-center gap-2">
                  <TickerLink ticker={s.ticker} className="text-fg" />
                  <Badge tone={m.tone}>{m.label}</Badge>
                  <span>at {money(s.price)}</span>
                </div>
                <p className="mt-0.5 text-xs text-faint">{m.explain}</p>
              </Row>
            );
          })}
        </Section>
      )}

      {buys.length > 0 && (
        <Section title="Buy signals — every check aligned" tone="green">
          {buys.map((s) => {
            const sz = (s.sizing ?? {}) as { shares?: number; position_value?: number };
            return (
              <Row key={s.id}>
                <div className="flex flex-wrap items-center gap-2">
                  <TickerLink ticker={s.ticker} className="text-fg" />
                  <span>
                    buy at {money(s.buy_point)} · exit if it falls to {money(s.stop_price)}
                  </span>
                </div>
                {sz.shares != null && (
                  <p className="mt-0.5 text-xs text-faint">
                    Suggested size: {sz.shares} shares (≈ {money(sz.position_value)})
                  </p>
                )}
              </Row>
            );
          })}
        </Section>
      )}

      <Section title={`Setups forming (${setups.length})`}>
        {setups.length === 0 && (
          <EmptyState>
            No stock is near its buy point right now. The screener keeps watching every
            evening — you&apos;ll get an email the moment one is ready.
          </EmptyState>
        )}
        {setups.map((r) => {
          const su = SETUP_META[r.setup_status ?? "none"] ?? SETUP_META.none;
          const watchReason = watches.find((w) => w.ticker === r.ticker)?.details as
            | { reason?: string }
            | undefined;
          return (
            <Row key={r.ticker}>
              <div className="flex flex-wrap items-center gap-2">
                <TickerLink ticker={r.ticker} className="text-fg" />
                <Badge tone={su.tone} title={su.explain}>
                  {su.label}
                </Badge>
                <span>buy point {money(r.vcp?.pivot ?? null)}</span>
                <span className="text-faint">· RS {r.rs_percentile ?? "—"}</span>
              </div>
              {watchReason?.reason && (
                <p className="mt-0.5 text-xs text-faint">{WATCH_REASON[watchReason.reason]}</p>
              )}
            </Row>
          );
        })}
      </Section>

      <Section title={`Your positions (${positions.length})`}>
        {positions.length === 0 && (
          <EmptyState>
            Nothing logged yet. When you take a buy signal, record it on the Positions page —
            the nightly check will then watch its stop and trend for you.
          </EmptyState>
        )}
        {positions.map((p) => (
          <Row key={p.id}>
            <div className="flex flex-wrap items-center gap-2">
              <TickerLink ticker={p.ticker} className="text-fg" />
              <span>
                {p.shares} shares @ {money(p.entry_price)}
              </span>
              <span className="text-faint">
                · exit if it falls to {money(p.stop_price ?? p.entry_price * 0.92)}
              </span>
            </div>
          </Row>
        ))}
      </Section>
    </main>
  );
}
