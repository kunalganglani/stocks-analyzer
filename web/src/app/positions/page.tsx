import { EmptyState } from "@/components/empty-state";
import { TickerLink } from "@/components/ticker-link";
import { money } from "@/lib/format";
import { closedPositions, lastCloses, openPositions, safe } from "@/lib/queries";
import { addPosition, closePosition, deletePosition, updateStop } from "../actions";

export const dynamic = "force-dynamic";

export default async function PositionsPage() {
  const open = await safe(() => openPositions(), []);
  const closed = await safe(() => closedPositions(), []);
  const closes = await safe(() => lastCloses(open.map((p) => p.ticker)), {});

  return (
    <main className="space-y-8 py-8">
      <section className="rounded-xl border border-border-ui bg-card p-5">
        <h2 className="mb-1 font-semibold">Log a buy</h2>
        <p className="mb-3 text-xs text-faint">
          Record what you bought so the nightly check can watch its stop and trend for you.
        </p>
        <form action={addPosition} className="grid grid-cols-2 gap-3 sm:grid-cols-6">
          <input name="ticker" placeholder="Ticker" required className={inp} />
          <input name="entry_price" type="number" step="0.01" placeholder="Entry $" required className={inp} />
          <input name="shares" type="number" step="1" placeholder="Shares" required className={inp} />
          <input name="entry_date" type="date" required className={inp} />
          <input name="stop_price" type="number" step="0.01" placeholder="Stop $ (optional)" className={inp} />
          <button className="rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-500">
            Add
          </button>
        </form>
        <p className="mt-2 text-xs text-faint">
          If you leave the stop empty it defaults to 8% below your entry — the most Minervini
          ever risks on one trade.
        </p>
      </section>

      <section>
        <h2 className="mb-3 font-semibold">Open ({open.length})</h2>
        <div className="space-y-3">
          {open.map((p) => {
            const last = closes[p.ticker];
            const stop = p.stop_price ?? Number((p.entry_price * 0.92).toFixed(2));
            const pnlPct = last ? (last / p.entry_price - 1) * 100 : null;
            const pnlUsd = last ? (last - p.entry_price) * p.shares : null;
            const stopDist = last ? ((last - stop) / last) * 100 : null;
            const meter =
              stopDist == null
                ? null
                : stopDist <= 0
                ? { cls: "bg-red-500", w: 4, text: "below stop — expect an exit alert" }
                : stopDist < 2
                ? { cls: "bg-red-500", w: 10, text: `${stopDist.toFixed(1)}% above stop — very close` }
                : stopDist < 5
                ? { cls: "bg-amber-500", w: 35, text: `${stopDist.toFixed(1)}% above stop` }
                : { cls: "bg-emerald-500", w: Math.min(100, stopDist * 4), text: `${stopDist.toFixed(1)}% above stop` };
            return (
              <div key={p.id} className="rounded-lg border border-border-ui bg-card-soft px-4 py-3 text-sm">
                <div className="grid grid-cols-2 items-center gap-x-4 gap-y-2 sm:flex sm:flex-wrap">
                  <TickerLink ticker={p.ticker} />
                  <span className="text-muted">
                    {p.shares} @ {money(p.entry_price)}
                  </span>
                  {last != null && <span className="text-muted">now {money(last)}</span>}
                  {pnlPct != null && (
                    <span
                      className={
                        pnlPct >= 0
                          ? "font-medium text-emerald-600 dark:text-emerald-400"
                          : "font-medium text-red-600 dark:text-red-400"
                      }
                    >
                      {pnlPct >= 0 ? "+" : ""}
                      {pnlPct.toFixed(1)}% ({money(pnlUsd)})
                    </span>
                  )}
                  <span className="text-faint">since {p.entry_date}</span>
                </div>

                {meter && (
                  <div className="mt-2 flex items-center gap-2">
                    <div className="h-1.5 w-32 overflow-hidden rounded bg-border-ui">
                      <div className={`h-full ${meter.cls}`} style={{ width: `${meter.w}%` }} />
                    </div>
                    <span className="text-xs text-faint">{meter.text}</span>
                  </div>
                )}

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <form action={updateStop} className="flex items-center gap-1">
                    <input type="hidden" name="id" value={p.id} />
                    <input
                      name="stop_price"
                      type="number"
                      step="0.01"
                      defaultValue={stop}
                      className="w-24 rounded border border-border-ui bg-input-bg px-2 py-1 text-xs"
                    />
                    <button className="rounded border border-border-ui px-2 py-1 text-xs text-muted hover:bg-card">
                      Update stop
                    </button>
                  </form>
                  <form action={closePosition} className="ml-auto flex items-center gap-1">
                    <input type="hidden" name="id" value={p.id} />
                    <input
                      name="exit_price"
                      type="number"
                      step="0.01"
                      placeholder="Exit $"
                      required
                      className="w-24 rounded border border-border-ui bg-input-bg px-2 py-1 text-xs"
                    />
                    <button className="rounded border border-amber-400 px-2 py-1 text-xs text-amber-700 hover:bg-card dark:border-amber-800 dark:text-amber-300">
                      Sold — record exit
                    </button>
                  </form>
                  <details className="relative">
                    <summary className="cursor-pointer list-none rounded border border-red-300 px-2 py-1 text-xs text-red-600 hover:bg-card dark:border-red-900 dark:text-red-400">
                      Remove
                    </summary>
                    <div className="absolute right-0 z-10 mt-1 w-56 rounded-lg border border-border-ui bg-card p-3 shadow-lg">
                      <p className="mb-2 text-xs text-muted">
                        Remove this position permanently? (Use &quot;Sold&quot; instead if you
                        actually exited.)
                      </p>
                      <form action={deletePosition}>
                        <input type="hidden" name="id" value={p.id} />
                        <button className="rounded bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-500">
                          Yes, remove
                        </button>
                      </form>
                    </div>
                  </details>
                </div>
              </div>
            );
          })}
          {open.length === 0 && (
            <EmptyState>
              Nothing here yet. When the dashboard shows a BUY and you take it, log it above —
              the nightly job will watch your stop, your gains, and the trend from then on.
            </EmptyState>
          )}
        </div>
      </section>

      <section>
        <h2 className="mb-3 font-semibold">Closed</h2>
        <div className="space-y-1 text-sm text-muted">
          {closed.map((p) => {
            const pnl = p.exit_price ? ((p.exit_price / p.entry_price - 1) * 100).toFixed(1) : null;
            return (
              <div key={p.id}>
                {p.ticker} — {p.shares} @ {money(p.entry_price)} → {money(p.exit_price)}{" "}
                {pnl && (
                  <span
                    className={
                      Number(pnl) >= 0
                        ? "text-emerald-600 dark:text-emerald-400"
                        : "text-red-600 dark:text-red-400"
                    }
                  >
                    ({pnl}%)
                  </span>
                )}{" "}
                closed {p.closed_at}
              </div>
            );
          })}
          {closed.length === 0 && <p className="text-faint">None yet.</p>}
        </div>
      </section>
    </main>
  );
}

const inp =
  "rounded-md border border-border-ui bg-input-bg px-3 py-2 text-sm text-fg outline-none focus:border-faint";
