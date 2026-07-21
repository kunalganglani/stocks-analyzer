import { EmptyState } from "@/components/empty-state";
import { fmtDate } from "@/lib/format";
import { latestScreenDate, safe, screenRows, strategyMeta } from "@/lib/queries";
import { ScreenerTable } from "./screener-table";

export const dynamic = "force-dynamic";

export default async function ScreenerPage() {
  const date = await safe(() => latestScreenDate(), null);
  const rows = date ? await safe(() => screenRows(date), []) : [];
  const meta = await safe(() => strategyMeta(), []);
  return (
    <main className="py-8">
      <h1 className="mb-1 text-lg font-semibold">Screener</h1>
      <p className="mb-6 text-sm text-muted">
        Every analyzed US stock, ranked by relative strength. Screened {fmtDate(date)}. Each
        strategy chip is a filter — a stock must pass every active strategy to show. Tap a row
        for the full checklist.
      </p>

      {rows.length > 0 ? (
        <ScreenerTable rows={rows} meta={meta} />
      ) : (
        <EmptyState>
          Nothing passes today. The quality scan runs every Sunday and this list refreshes after
          each US market close — an empty list can also simply mean the market is weak, which is
          the tool telling you to be patient.
        </EmptyState>
      )}
    </main>
  );
}
