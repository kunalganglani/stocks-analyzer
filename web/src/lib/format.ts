export function money(x: number | null | undefined): string {
  return x == null
    ? "—"
    : `$${Number(x).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

export function pct(x: number | null | undefined, digits = 1): string {
  return x == null ? "—" : `${(Number(x) * 100).toFixed(digits)}%`;
}

/** "2026-07-20" -> "Mon, Jul 20" */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "never";
  const d = new Date(`${iso}T12:00:00Z`);
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

/** Previous US weekday (UTC approximation; market holidays tolerated as a
    false "maybe stale" — the copy hedges accordingly). */
export function isScreenStale(screenDate: string | null | undefined): boolean {
  if (!screenDate) return false; // "never" state has its own messaging
  const now = new Date();
  const prev = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  do {
    prev.setUTCDate(prev.getUTCDate() - 1);
  } while (prev.getUTCDay() === 0 || prev.getUTCDay() === 6);
  return screenDate < prev.toISOString().slice(0, 10);
}
