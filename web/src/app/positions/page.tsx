import { addPosition, closePosition, deletePosition, updateStop } from "../actions";
import { closedPositions, lastCloses, openPositions, safe } from "@/lib/queries";

export const dynamic = "force-dynamic";

const money = (x: number | null | undefined) =>
  x == null ? "—" : `$${Number(x).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;

export default async function PositionsPage() {
  const open = await safe(() => openPositions(), []);
  const closed = await safe(() => closedPositions(), []);
  const closes = await safe(() => lastCloses(open.map((p) => p.ticker)), {});

  return (
    <main className="space-y-8 py-8">
      <section className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
        <h2 className="mb-3 font-semibold">Log a buy</h2>
        <form action={addPosition} className="grid grid-cols-2 gap-3 sm:grid-cols-6">
          <input name="ticker" placeholder="Ticker" required className={inp} />
          <input name="entry_price" type="number" step="0.01" placeholder="Entry $" required className={inp} />
          <input name="shares" type="number" step="1" placeholder="Shares" required className={inp} />
          <input name="entry_date" type="date" required className={inp} />
          <input name="stop_price" type="number" step="0.01" placeholder="Stop $ (opt)" className={inp} />
          <button className="rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-500">
            Add
          </button>
        </form>
        <p className="mt-2 text-xs text-zinc-500">
          Stop defaults to entry − 8% (Minervini max). The daily job watches every position.
        </p>
      </section>

      <section>
        <h2 className="mb-3 font-semibold">Open ({open.length})</h2>
        <div className="space-y-3">
          {open.map((p) => {
            const last = closes[p.ticker];
            const pnl = last ? ((last / p.entry_price - 1) * 100).toFixed(1) : null;
            return (
              <div key={p.id} className="flex flex-wrap items-center gap-4 rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-3 text-sm">
                <span className="w-14 font-semibold">{p.ticker}</span>
                <span>{p.shares} @ {money(p.entry_price)}</span>
                <span className="text-zinc-400">since {p.entry_date}</span>
                {pnl && (
                  <span className={Number(pnl) >= 0 ? "text-emerald-400" : "text-red-400"}>
                    {pnl}%
                  </span>
                )}
                <form action={updateStop} className="flex items-center gap-1">
                  <input type="hidden" name="id" value={p.id} />
                  <input
                    name="stop_price"
                    type="number"
                    step="0.01"
                    defaultValue={p.stop_price ?? Number((p.entry_price * 0.92).toFixed(2))}
                    className="w-24 rounded border border-zinc-700 bg-zinc-800 px-2 py-1 text-xs"
                  />
                  <button className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-300 hover:bg-zinc-800">
                    set stop
                  </button>
                </form>
                <form action={closePosition} className="ml-auto flex items-center gap-1">
                  <input type="hidden" name="id" value={p.id} />
                  <input name="exit_price" type="number" step="0.01" placeholder="Exit $" required
                    className="w-24 rounded border border-zinc-700 bg-zinc-800 px-2 py-1 text-xs" />
                  <button className="rounded border border-amber-800 px-2 py-1 text-xs text-amber-300 hover:bg-zinc-800">
                    close
                  </button>
                </form>
                <form action={deletePosition}>
                  <input type="hidden" name="id" value={p.id} />
                  <button className="rounded border border-red-900 px-2 py-1 text-xs text-red-400 hover:bg-zinc-800">
                    ✕
                  </button>
                </form>
              </div>
            );
          })}
          {open.length === 0 && <p className="text-sm text-zinc-500">No open positions.</p>}
        </div>
      </section>

      <section>
        <h2 className="mb-3 font-semibold">Closed</h2>
        <div className="space-y-1 text-sm text-zinc-400">
          {closed.map((p) => {
            const pnl = p.exit_price ? ((p.exit_price / p.entry_price - 1) * 100).toFixed(1) : null;
            return (
              <div key={p.id}>
                {p.ticker} — {p.shares} @ {money(p.entry_price)} → {money(p.exit_price)}{" "}
                {pnl && (
                  <span className={Number(pnl) >= 0 ? "text-emerald-400" : "text-red-400"}>
                    ({pnl}%)
                  </span>
                )}{" "}
                closed {p.closed_at}
              </div>
            );
          })}
          {closed.length === 0 && <p className="text-zinc-500">None yet.</p>}
        </div>
      </section>
    </main>
  );
}

const inp =
  "rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-zinc-500";
