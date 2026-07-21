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

const money = (x: number | null | undefined) =>
  x == null ? "—" : `$${Number(x).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;

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
  const riskOn = regime?.risk_on;

  const buys = signals.filter((s) => s.type === "BUY");
  const sells = signals.filter((s) => s.type.startsWith("SELL") || s.type === "CLIMAX_WARN");
  const watches = signals.filter((s) => s.type === "WATCH");

  return (
    <main className="space-y-8 py-8">
      <section className="flex flex-wrap items-center gap-4">
        <div
          className={`rounded-lg px-4 py-3 font-medium ${
            riskOn == null
              ? "bg-zinc-800 text-zinc-300"
              : riskOn
              ? "bg-emerald-900/60 text-emerald-300"
              : "bg-red-900/60 text-red-300"
          }`}
        >
          {riskOn == null
            ? "No run data yet"
            : riskOn
            ? "RISK-ON — SPY & QQQ above 200d MA"
            : "RISK-OFF — buy signals suppressed"}
        </div>
        <div className="text-sm text-zinc-400">
          Last screen: {date ?? "never"} · Quality universe: {quality} stocks ·{" "}
          {run?.status === "failed" ? (
            <span className="text-red-400">last run FAILED</span>
          ) : (
            `run ${run?.status ?? "n/a"}`
          )}
        </div>
        <RunNowButton />
      </section>

      {sells.length > 0 && (
        <Section title="⚠ Protect positions" tone="red">
          {sells.map((s) => (
            <Row key={s.id}>
              <b>{s.ticker}</b> — {s.type} at {money(s.price)}
            </Row>
          ))}
        </Section>
      )}

      {buys.length > 0 && (
        <Section title="BUY signals — all gates aligned" tone="green">
          {buys.map((s) => (
            <Row key={s.id}>
              <b>{s.ticker}</b> — buy point {money(s.buy_point)}, stop {money(s.stop_price)}
              {s.sizing ? ` · ${String((s.sizing as Record<string, unknown>).shares)} shares` : ""}
            </Row>
          ))}
        </Section>
      )}

      {buys.length === 0 && sells.length === 0 && (
        <p className="text-zinc-400">
          No action today.{" "}
          {watches.length > 0
            ? `${watches.length} setup(s) forming — see below.`
            : "The tool is waiting for high-conviction alignment (quality + trend + entry + market)."}
        </p>
      )}

      <Section title={`Setups forming (${setups.length})`}>
        {setups.length === 0 && <p className="text-sm text-zinc-500">None near a pivot.</p>}
        {setups.map((r) => (
          <Row key={r.ticker}>
            <b>{r.ticker}</b> — {r.setup_status} · pivot {money(r.vcp?.pivot ?? null)} · RS{" "}
            {r.rs_percentile ?? "—"}
          </Row>
        ))}
      </Section>

      <Section title={`Open positions (${positions.length})`}>
        {positions.length === 0 && (
          <p className="text-sm text-zinc-500">None — add one when you take a buy signal.</p>
        )}
        {positions.map((p) => (
          <Row key={p.id}>
            <b>{p.ticker}</b> — {p.shares} @ {money(p.entry_price)} · stop{" "}
            {money(p.stop_price ?? p.entry_price * 0.92)}
          </Row>
        ))}
      </Section>
    </main>
  );
}

function Section({
  title,
  tone,
  children,
}: {
  title: string;
  tone?: "red" | "green";
  children: React.ReactNode;
}) {
  const border =
    tone === "red" ? "border-red-900" : tone === "green" ? "border-emerald-900" : "border-zinc-800";
  return (
    <section className={`rounded-xl border ${border} bg-zinc-900/50 p-5`}>
      <h2 className="mb-3 font-semibold">{title}</h2>
      <div className="space-y-2">{children}</div>
    </section>
  );
}

function Row({ children }: { children: React.ReactNode }) {
  return <div className="text-sm text-zinc-300">{children}</div>;
}
