import { recentSignals, safe } from "@/lib/queries";

export const dynamic = "force-dynamic";

const badge: Record<string, string> = {
  BUY: "bg-emerald-900/60 text-emerald-300",
  WATCH: "bg-amber-900/60 text-amber-300",
  SELL_STOP: "bg-red-900/60 text-red-300",
  SELL_STRENGTH: "bg-sky-900/60 text-sky-300",
  SELL_TRAIL_50D: "bg-red-900/40 text-red-300",
  SELL_200D: "bg-red-900/60 text-red-300",
  CLIMAX_WARN: "bg-purple-900/60 text-purple-300",
};

export default async function SignalsPage() {
  const signals = await safe(() => recentSignals(90), []);
  return (
    <main className="py-8">
      <h1 className="mb-6 text-lg font-semibold">Signal history (90 days)</h1>
      <div className="space-y-2">
        {signals.map((s) => (
          <div
            key={s.id}
            className="flex flex-wrap items-center gap-3 rounded-lg border border-zinc-900 bg-zinc-900/30 px-4 py-2 text-sm"
          >
            <span className="w-24 text-zinc-500">{s.signal_date}</span>
            <span className="w-14 font-semibold">{s.ticker}</span>
            <span className={`rounded px-2 py-0.5 text-xs ${badge[s.type] ?? "bg-zinc-800"}`}>
              {s.type}
            </span>
            {s.buy_point != null && <span>buy {`$${Number(s.buy_point).toFixed(2)}`}</span>}
            {s.stop_price != null && <span>stop {`$${Number(s.stop_price).toFixed(2)}`}</span>}
            {s.price != null && <span className="text-zinc-400">last {`$${Number(s.price).toFixed(2)}`}</span>}
          </div>
        ))}
        {signals.length === 0 && <p className="text-sm text-zinc-500">No signals yet.</p>}
      </div>
    </main>
  );
}
