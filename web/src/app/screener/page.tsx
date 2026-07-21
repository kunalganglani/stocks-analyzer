import { Badge } from "@/components/badge";
import { EmptyState } from "@/components/empty-state";
import { TickerLink } from "@/components/ticker-link";
import { fmtDate, money } from "@/lib/format";
import { SETUP_META, TT_CRITERIA_LABELS } from "@/lib/labels";
import { latestScreenDate, safe, screenRows } from "@/lib/queries";

export const dynamic = "force-dynamic";

const grid = "grid grid-cols-3 items-center gap-2 sm:grid-cols-[1.2fr_1fr_0.8fr_1fr_1.1fr_1fr]";

export default async function ScreenerPage() {
  const date = await safe(() => latestScreenDate(), null);
  const rows = date ? await safe(() => screenRows(date), []) : [];
  return (
    <main className="py-8">
      <h1 className="mb-1 text-lg font-semibold">Strong stocks</h1>
      <p className="mb-6 text-sm text-muted">
        Every stock here passed all 8 trend checks (Minervini&apos;s Trend Template), ranked by
        relative strength. Screened {fmtDate(date)}. Tap a row to see why it qualifies.
      </p>

      <div className={`${grid} hidden border-b border-border-ui pb-2 text-left text-xs text-faint sm:grid`}>
        <span>Ticker</span>
        <span>Price</span>
        <span title="Relative strength — how this stock's performance ranks against every other US stock (higher is stronger)" className="cursor-help">
          Strength ⓘ
        </span>
        <span>Off 52w high</span>
        <span>Setup</span>
        <span>Buy point</span>
      </div>

      {rows.map((r) => {
        const su = SETUP_META[r.setup_status ?? "none"] ?? SETUP_META.none;
        const cons = r.vcp?.contractions ?? [];
        const lastDepth = cons.length ? cons[cons.length - 1].depth : null;
        const dryup = r.vcp?.dryup_ratio;
        return (
          <details key={r.ticker} className="border-b border-border-soft">
            <summary className={`${grid} cursor-pointer list-none py-2.5 text-sm hover:bg-card-soft`}>
              <TickerLink ticker={r.ticker} />
              <span>{money(r.close)}</span>
              <span title={r.rs_percentile != null ? `Stronger than ${r.rs_percentile}% of all US stocks` : undefined}>
                {r.rs_percentile ?? "—"}
              </span>
              <span className="text-muted">
                {r.pct_off_52w_high == null ? "—" : `${(r.pct_off_52w_high * 100).toFixed(1)}%`}
              </span>
              <span>
                <Badge tone={su.tone} title={su.explain}>
                  {su.label}
                </Badge>
              </span>
              <span>{money(r.vcp?.pivot ?? null)}</span>
            </summary>
            <div className="grid gap-4 pb-4 pt-1 text-xs text-muted sm:grid-cols-2">
              <div>
                <p className="mb-1 font-medium text-fg">Why it qualifies</p>
                <ul className="space-y-0.5">
                  {Object.entries(TT_CRITERIA_LABELS).map(([k, label]) => (
                    <li key={k}>
                      <span className="text-emerald-600 dark:text-emerald-400">✓</span> {label}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="mb-1 font-medium text-fg">Entry setup</p>
                {cons.length > 0 ? (
                  <p className="leading-relaxed">
                    {cons.length} tightening pullback{cons.length > 1 ? "s" : ""} (
                    {cons.map((c) => `−${(c.depth * 100).toFixed(1)}%`).join(" → ")})
                    {lastDepth != null && lastDepth <= 0.12 && ", now calm"}
                    {dryup != null && dryup < 0.8 && "; volume drying up — sellers exhausted"}.
                    {r.vcp?.pivot != null && (
                      <> Buy point: {money(r.vcp.pivot)} on a strong-volume push above it.</>
                    )}
                  </p>
                ) : (
                  <p>No calm base yet — strong trend, but no low-risk entry point has formed.</p>
                )}
              </div>
            </div>
          </details>
        );
      })}

      {rows.length === 0 && (
        <EmptyState>
          Nothing passes today. The quality scan runs every Sunday and this list refreshes after
          each US market close — an empty list can also simply mean the market is weak, which is
          the tool telling you to be patient.
        </EmptyState>
      )}
    </main>
  );
}
