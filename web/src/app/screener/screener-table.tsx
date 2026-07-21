"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/badge";
import { EmptyState } from "@/components/empty-state";
import { TickerLink } from "@/components/ticker-link";
import { money } from "@/lib/format";
import { checkLabel, SETUP_META } from "@/lib/labels";

// Local row/meta types: queries.ts is server-only, so shapes are mirrored here.
export type Verdict = { pass: boolean; checks: Record<string, boolean> };
export type Row = {
  ticker: string;
  close: number | null;
  rs_percentile: number | null;
  pct_off_52w_high: number | null;
  setup_status: string | null;
  tt_pass: boolean;
  tt_criteria: Record<string, boolean> | null;
  strategies: Record<string, Verdict> | null;
  vcp: {
    pivot?: number | null;
    status?: string;
    contractions?: { depth: number }[];
    dryup_ratio?: number | null;
  } | null;
};
export type Meta = { key: string; name: string; description: string };

const grid = "grid grid-cols-3 items-center gap-2 sm:grid-cols-[1.2fr_1fr_0.8fr_1fr_1.1fr_1fr]";

const SETUP_FILTERS = [
  { key: "all", label: "Any setup" },
  { key: "breakout", label: "BUY zone" },
  { key: "pivot_near", label: "Almost ready" },
  { key: "base_forming", label: "Building base" },
] as const;

/** Older rows predate per-strategy storage: they were quality passers by
    construction, so synthesize verdicts from what we know. */
function verdicts(r: Row): Record<string, Verdict> {
  if (r.strategies) return r.strategies;
  return {
    minervini: { pass: r.tt_pass, checks: r.tt_criteria ?? {} },
    buffett: { pass: true, checks: {} },
    munger: { pass: true, checks: {} },
  };
}

export function ScreenerTable({ rows, meta }: { rows: Row[]; meta: Meta[] }) {
  const strategyKeys = meta.length
    ? meta.map((m) => m.key)
    : ["minervini", "buffett", "munger"];
  const metaByKey = Object.fromEntries(meta.map((m) => [m.key, m]));

  const [query, setQuery] = useState("");
  const [setup, setSetup] = useState<(typeof SETUP_FILTERS)[number]["key"]>("all");
  const [active, setActive] = useState<Record<string, boolean>>(
    Object.fromEntries(strategyKeys.map((k) => [k, true]))
  );

  const visible = useMemo(() => {
    const q = query.trim().toUpperCase();
    return rows.filter((r) => {
      if (q && !r.ticker.toUpperCase().includes(q)) return false;
      if (setup !== "all" && r.setup_status !== setup) return false;
      const v = verdicts(r);
      return strategyKeys.every((k) => !active[k] || v[k]?.pass);
    });
  }, [rows, query, setup, active, strategyKeys]);

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="text-xs text-faint">Strategies (must pass):</span>
        {strategyKeys.map((k) => {
          const on = !!active[k];
          const m = metaByKey[k];
          const count = rows.filter((r) => verdicts(r)[k]?.pass).length;
          return (
            <button
              key={k}
              onClick={() => setActive((a) => ({ ...a, [k]: !a[k] }))}
              title={m?.description}
              className={`rounded-full border px-3 py-1 text-xs ${
                on
                  ? "border-emerald-600 bg-emerald-600 text-white"
                  : "border-border-ui text-muted line-through opacity-70 hover:opacity-100"
              }`}
            >
              {m?.name ?? k} <span className="ml-1 opacity-70">{count}</span>
            </button>
          );
        })}
      </div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search ticker…"
          className="w-40 rounded-md border border-border-ui bg-input-bg px-3 py-1.5 text-sm text-fg outline-none focus:border-faint"
        />
        <div className="flex flex-wrap gap-1">
          {SETUP_FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setSetup(f.key)}
              className={`rounded-full border px-3 py-1 text-xs ${
                setup === f.key
                  ? "border-sky-600 bg-sky-600 text-white"
                  : "border-border-ui text-muted hover:text-fg"
              }`}
            >
              {f.label}
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

      {visible.slice(0, 300).map((r) => {
        const su = SETUP_META[r.setup_status ?? "none"] ?? SETUP_META.none;
        const v = verdicts(r);
        const cons = r.vcp?.contractions ?? [];
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
            <div className="grid gap-4 pb-4 pt-1 text-xs text-muted sm:grid-cols-3">
              {strategyKeys.map((k) => {
                const sv = v[k];
                const m = metaByKey[k];
                return (
                  <div key={k}>
                    <p className="mb-1 font-medium text-fg">
                      {m?.name ?? k}{" "}
                      <span className={sv?.pass ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}>
                        {sv?.pass ? "pass" : "fail"}
                      </span>
                    </p>
                    <ul className="space-y-0.5">
                      {Object.entries(sv?.checks ?? {}).map(([ck, ok]) => (
                        <li key={ck}>
                          {ok ? (
                            <span className="text-emerald-600 dark:text-emerald-400">✓</span>
                          ) : (
                            <span className="text-red-600 dark:text-red-400">✗</span>
                          )}{" "}
                          {checkLabel(ck)}
                        </li>
                      ))}
                      {Object.keys(sv?.checks ?? {}).length === 0 && <li>details pending next screen</li>}
                    </ul>
                  </div>
                );
              })}
              <div className="sm:col-span-3">
                <p className="mb-1 font-medium text-fg">Entry setup</p>
                {cons.length > 0 ? (
                  <p className="leading-relaxed">
                    {cons.length} tightening pullback{cons.length > 1 ? "s" : ""} (
                    {cons.map((c) => `−${(c.depth * 100).toFixed(1)}%`).join(" → ")})
                    {dryup != null && dryup < 0.8 && "; volume drying up — sellers exhausted"}.
                    {r.vcp?.pivot != null && (
                      <> Buy point: {money(r.vcp.pivot)} on a strong-volume push above it.</>
                    )}
                  </p>
                ) : (
                  <p>No calm base yet — no low-risk entry point has formed.</p>
                )}
              </div>
            </div>
          </details>
        );
      })}

      {visible.length > 300 && (
        <p className="py-3 text-center text-xs text-faint">
          Showing top 300 by strength — narrow with search or filters to see the rest.
        </p>
      )}
      {visible.length === 0 && rows.length > 0 && (
        <EmptyState>No stocks match your filters.</EmptyState>
      )}
    </div>
  );
}
