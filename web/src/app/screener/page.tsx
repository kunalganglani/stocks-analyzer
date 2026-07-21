import { latestScreenDate, safe, screenRows } from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function ScreenerPage() {
  const date = await safe(() => latestScreenDate(), null);
  const rows = date ? await safe(() => screenRows(date), []) : [];
  return (
    <main className="py-8">
      <h1 className="mb-1 text-lg font-semibold">Trend Template passers</h1>
      <p className="mb-6 text-sm text-zinc-400">
        {date ? `Screen date ${date}` : "No screen data yet — run the daily job."} · all 8
        Minervini criteria passed · ranked by relative strength
      </p>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-800 text-left text-zinc-500">
            <th className="py-2">Ticker</th>
            <th>Close</th>
            <th>RS %ile</th>
            <th>Off 52w high</th>
            <th>Setup</th>
            <th>Pivot</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.ticker} className="border-b border-zinc-900">
              <td className="py-2 font-medium">{r.ticker}</td>
              <td>{r.close == null ? "—" : `$${r.close.toFixed(2)}`}</td>
              <td>{r.rs_percentile ?? "—"}</td>
              <td>{r.pct_off_52w_high == null ? "—" : `${(r.pct_off_52w_high * 100).toFixed(1)}%`}</td>
              <td>
                <SetupBadge status={r.setup_status} />
              </td>
              <td>{r.vcp?.pivot == null ? "—" : `$${Number(r.vcp.pivot).toFixed(2)}`}</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={6} className="py-6 text-zinc-500">
                Nothing passes today.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </main>
  );
}

function SetupBadge({ status }: { status: string | null }) {
  const styles: Record<string, string> = {
    breakout: "bg-emerald-900/60 text-emerald-300",
    pivot_near: "bg-amber-900/60 text-amber-300",
    base_forming: "bg-zinc-800 text-zinc-400",
    none: "text-zinc-600",
  };
  return (
    <span className={`rounded px-2 py-0.5 text-xs ${styles[status ?? "none"] ?? ""}`}>
      {status ?? "—"}
    </span>
  );
}
