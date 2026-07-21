"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/badge";
import { EmptyState } from "@/components/empty-state";
import { TickerLink } from "@/components/ticker-link";
import { money } from "@/lib/format";
import { SETUP_META, TT_CRITERIA_LABELS } from "@/lib/labels";

// Local row type: queries.ts is server-only, so the shape is mirrored here.
export type Row = {
  ticker: string;
  close: number | null;
  rs_percentile: number | null;
  pct_off_52w_high: number | null;
  setup_status: string | null;
  tt_criteria: Record<string, boolean> | null;
  vcp: {
    pivot?: number | null;
    status?: string;
    contractions?: { depth: number }[];
    dryup_ratio?: number | null;
  } | null;
};

const grid = "grid grid-cols-3 items-center gap-2 sm:grid-cols-[1.2fr_1fr_0.8fr_1fr_1.1fr_1fr]";

const FILTERS = [
  { key: "all", label: "All" },
  { key: "breakout", label: "BUY zone" },
  { key: "pivot_near", label: "Almost ready" },
  { key: "base_forming", label: "Building base" },
] as const;

export function ScreenerTable({ rows }: { rows: Row[] }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["key"]>("all");

  const visible = useMemo(() => {
    const q = query.trim().toUpperCase();
    return rows.filter(
      (r) =>
        (filter === "all" || r.setup_status === filter) &&
        (!q || r.ticker.toUpperCase().includes(q))
    );
  }, [rows, query, filter]);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search ticker…"
          className="w-40 rounded-md border border-border-ui bg-input-bg px-3 py-1.5 text-sm text-fg outline-none focus:border-faint"
        />
        <div className="flex flex-wrap gap-1">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`rounded-full border px-3 py-1 text-xs ${
                filter === f.key
                  ? "border-emerald-600 bg-emerald-600 text-white"
                  : "border-border-ui text-muted hover:text-fg"
              }`}
            >
              {f.label}
              {f.key !== "all" && (
                <span className="ml-1 opacity-70">
                  {rows.filter((r) => r.setup_status === f.key).length}
                </span>
              )}
            </button>
          ))}
        </div>
        <span className="ml-auto text-xs text-faint">
          {visible.length} of {rows.length}
        </span>
      </div>

      <div className={`${grid} hidden border-b border-border-ui pb-2 text-left text-xs text-faint sm:grid`}>
        <span>Ticker</span>
        <span>Price</span>
        <span
          title="Relative strength — how this stock's performance ranks against every other US stock (higher is stronger)"
          className="cursor-help"
        >
          Strength ⓘ
        </span>
        <span>Off 52w high</span>
        <span>Setup</span>
        <span>Buy point</span>
      </div>

      {visible.map((r) => {
        const su = SETUP_META[r.setup_status ?? "none"] ?? SETUP_META.none;
        const cons = r.vcp?.contractions ?? [];
        const lastDepth = cons.length ? cons[cons.length - 1].depth : null;
        const dryup = r.vcp?.dryup_ratio;
        return (
          <details key={r.ticker} className="border-b border-border-soft">
            <summary className={`${grid} cursor-pointer list-none py-2.5 text-sm hover:bg-card-soft`}>
              <TickerLink ticker={r.ticker} />
              <span>{money(r.close)}</span>
              <span
                title={
                  r.rs_percentile != null
                    ? `Stronger than ${r.rs_percentile}% of all US stocks`
                    : undefined
                }
              >
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

      {visible.length === 0 && rows.length > 0 && (
        <EmptyState>No stocks match your search/filter.</EmptyState>
      )}
    </div>
  );
}
