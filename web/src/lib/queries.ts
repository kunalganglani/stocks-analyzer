import "server-only";
import { supabase } from "./supabase";

// Renders pages usable before Supabase env vars exist (first deploy).
export async function safe<T>(p: Promise<T> | (() => Promise<T>), fallback: T): Promise<T> {
  try {
    return await (typeof p === "function" ? p() : p);
  } catch {
    return fallback;
  }
}

export type Signal = {
  id: number;
  signal_date: string;
  ticker: string;
  type: string;
  price: number | null;
  buy_point: number | null;
  stop_price: number | null;
  sizing: Record<string, unknown> | null;
  details: Record<string, unknown> | null;
  position_id: number | null;
};

export type Position = {
  id: number;
  ticker: string;
  entry_price: number;
  shares: number;
  entry_date: string;
  stop_price: number | null;
  status: string;
  notes: string | null;
};

export type ScreenRow = {
  ticker: string;
  close: number | null;
  rs_percentile: number | null;
  pct_off_52w_high: number | null;
  setup_status: string | null;
  tt_pass: boolean;
  tt_criteria: Record<string, boolean> | null;
  vcp: {
    pivot?: number | null;
    status?: string;
    contractions?: { depth: number }[];
    dryup_ratio?: number | null;
  } | null;
};

export async function latestRun() {
  const sb = supabase();
  const { data } = await sb
    .from("runs").select("*").eq("kind", "daily")
    .order("started_at", { ascending: false }).limit(1);
  return data?.[0] ?? null;
}

export async function latestScreenDate(): Promise<string | null> {
  const sb = supabase();
  const { data } = await sb
    .from("daily_screens").select("screen_date")
    .order("screen_date", { ascending: false }).limit(1);
  return data?.[0]?.screen_date ?? null;
}

export async function screenRows(date: string): Promise<ScreenRow[]> {
  const sb = supabase();
  const { data } = await sb
    .from("daily_screens")
    .select("ticker,close,rs_percentile,pct_off_52w_high,setup_status,tt_pass,tt_criteria,vcp")
    .eq("screen_date", date).eq("tt_pass", true)
    .order("rs_percentile", { ascending: false });
  return (data as ScreenRow[]) ?? [];
}

export async function recentSignals(days = 30): Promise<Signal[]> {
  const sb = supabase();
  const cutoff = new Date(Date.now() - days * 86400_000).toISOString().slice(0, 10);
  const { data } = await sb
    .from("signals").select("*").gte("signal_date", cutoff)
    .order("signal_date", { ascending: false }).order("id", { ascending: false });
  return (data as Signal[]) ?? [];
}

export async function openPositions(): Promise<Position[]> {
  const sb = supabase();
  const { data } = await sb
    .from("positions").select("*").eq("status", "open")
    .order("entry_date", { ascending: false });
  return (data as Position[]) ?? [];
}

export async function closedPositions(): Promise<(Position & { exit_price: number | null; closed_at: string | null })[]> {
  const sb = supabase();
  const { data } = await sb
    .from("positions").select("*").eq("status", "closed")
    .order("closed_at", { ascending: false }).limit(50);
  return data ?? [];
}

export async function lastCloses(tickers: string[]): Promise<Record<string, number>> {
  if (tickers.length === 0) return {};
  const sb = supabase();
  const date = await latestScreenDate();
  if (!date) return {};
  const { data } = await sb
    .from("daily_screens").select("ticker,close")
    .eq("screen_date", date).in("ticker", tickers);
  return Object.fromEntries((data ?? []).map((r) => [r.ticker, r.close]));
}

export async function qualityCount(): Promise<number> {
  const sb = supabase();
  const { count } = await sb
    .from("quality_universe").select("*", { count: "exact", head: true })
    .eq("passes", true);
  return count ?? 0;
}
