"use server";

import { revalidatePath } from "next/cache";
import { supabase } from "@/lib/supabase";

// --- on-demand screener run: dispatches the daily GitHub Actions workflow ---
export async function triggerRun(): Promise<{ ok: boolean; error?: string }> {
  const pat = process.env.GH_PAT;
  const repo = process.env.GH_REPO; // e.g. kunalganglani/stocks-analyzer
  if (!pat || !repo) {
    return { ok: false, error: "Run-now not configured (GH_PAT / GH_REPO)" };
  }
  try {
    const res = await fetch(
      `https://api.github.com/repos/${repo}/actions/workflows/daily-screen.yml/dispatches`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${pat}`,
          Accept: "application/vnd.github+json",
          "X-GitHub-Api-Version": "2022-11-28",
        },
        body: JSON.stringify({ ref: "main" }),
      }
    );
    if (res.status !== 204) {
      return { ok: false, error: `GitHub ${res.status}: ${(await res.text()).slice(0, 200)}` };
    }
    return { ok: true };
  } catch (e) {
    return { ok: false, error: String(e).slice(0, 200) };
  }
}

// --- positions CRUD ---
export async function addPosition(formData: FormData): Promise<void> {
  const sb = supabase();
  const ticker = String(formData.get("ticker") ?? "").trim().toUpperCase();
  const entry = Number(formData.get("entry_price"));
  const shares = Number(formData.get("shares"));
  const entryDate = String(formData.get("entry_date") ?? "");
  const stopRaw = String(formData.get("stop_price") ?? "").trim();
  if (!ticker || !entry || !shares || !entryDate) return;
  await sb.from("positions").insert({
    ticker,
    entry_price: entry,
    shares,
    entry_date: entryDate,
    stop_price: stopRaw ? Number(stopRaw) : Number((entry * 0.92).toFixed(4)),
    notes: String(formData.get("notes") ?? "") || null,
  });
  revalidatePath("/positions");
  revalidatePath("/");
}

export async function closePosition(formData: FormData): Promise<void> {
  const sb = supabase();
  const id = Number(formData.get("id"));
  const exit = Number(formData.get("exit_price"));
  if (!id || !exit) return;
  await sb
    .from("positions")
    .update({
      status: "closed",
      exit_price: exit,
      closed_at: new Date().toISOString().slice(0, 10),
    })
    .eq("id", id);
  revalidatePath("/positions");
  revalidatePath("/");
}

export async function deletePosition(formData: FormData): Promise<void> {
  const sb = supabase();
  const id = Number(formData.get("id"));
  if (!id) return;
  await sb.from("positions").delete().eq("id", id);
  revalidatePath("/positions");
  revalidatePath("/");
}

export async function updateStop(formData: FormData): Promise<void> {
  const sb = supabase();
  const id = Number(formData.get("id"));
  const stop = Number(formData.get("stop_price"));
  if (!id || !stop) return;
  await sb.from("positions").update({ stop_price: stop }).eq("id", id);
  revalidatePath("/positions");
  revalidatePath("/");
}
