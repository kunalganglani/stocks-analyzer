import { Badge } from "@/components/badge";
import { EmptyState } from "@/components/empty-state";
import { TickerLink } from "@/components/ticker-link";
import { fmtDate, money } from "@/lib/format";
import { signalMeta, WATCH_REASON } from "@/lib/labels";
import { recentSignals, safe, type Signal } from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function SignalsPage() {
  const signals = await safe(() => recentSignals(90), []);
  const byDate = signals.reduce<Record<string, Signal[]>>((acc, s) => {
    (acc[s.signal_date] ??= []).push(s);
    return acc;
  }, {});

  return (
    <main className="py-8">
      <h1 className="mb-1 text-lg font-semibold">Signal history</h1>
      <p className="mb-6 text-sm text-muted">
        Everything the tool has flagged in the last 90 days, newest first.
      </p>
      <div className="space-y-6">
        {Object.entries(byDate).map(([d, rows]) => (
          <section key={d}>
            <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-faint">
              {fmtDate(d)}
            </h2>
            <div className="space-y-2">
              {rows.map((s) => {
                const m = signalMeta(s.type);
                const reason = (s.details as { reason?: string } | null)?.reason;
                const sz = (s.sizing ?? {}) as {
                  shares?: number;
                  position_value?: number;
                  risk_dollars?: number;
                };
                return (
                  <div
                    key={s.id}
                    className="rounded-lg border border-border-soft bg-card-soft px-4 py-2.5 text-sm"
                  >
                    <div className="flex flex-wrap items-center gap-3">
                      <TickerLink ticker={s.ticker} className="w-14" />
                      <Badge tone={m.tone} title={m.explain}>
                        {m.label}
                      </Badge>
                      {s.buy_point != null && <span>buy {money(s.buy_point)}</span>}
                      {s.stop_price != null && (
                        <span className="text-muted">stop {money(s.stop_price)}</span>
                      )}
                      {s.price != null && <span className="text-faint">last {money(s.price)}</span>}
                    </div>
                    {(reason || s.type === "BUY") && (
                      <p className="mt-1 text-xs text-faint">
                        {reason
                          ? WATCH_REASON[reason] ?? reason
                          : sz.shares != null
                          ? `Suggested ${sz.shares} shares (≈ ${money(sz.position_value)}), risking ~${money(sz.risk_dollars)}`
                          : m.explain}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        ))}
        {signals.length === 0 && (
          <EmptyState>
            No signals yet. They appear here after each evening&apos;s screen — buys, warnings,
            and everything in between.
          </EmptyState>
        )}
      </div>
    </main>
  );
}
