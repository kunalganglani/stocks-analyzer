"use server";

import { revalidatePath } from "next/cache";
import { GoogleAuth } from "google-auth-library";
import { supabase } from "@/lib/supabase";

// --- on-demand screener run: fires the Cloud Build trigger used by Cloud Scheduler ---
export async function triggerRun(): Promise<{ ok: boolean; error?: string }> {
  const saKey = process.env.GCP_SA_KEY;
  const project = process.env.GCP_PROJECT;
  const trigger = process.env.CLOUD_BUILD_TRIGGER_ID;
  if (!saKey || !project || !trigger) {
    return { ok: false, error: "Run-now not configured (GCP_SA_KEY / GCP_PROJECT / CLOUD_BUILD_TRIGGER_ID)" };
  }
  try {
    const auth = new GoogleAuth({
      credentials: JSON.parse(saKey),
      scopes: ["https://www.googleapis.com/auth/cloud-platform"],
    });
    const token = await (await auth.getClient()).getAccessToken();
    const region = process.env.CLOUD_BUILD_REGION ?? "us-central1";
    const res = await fetch(
      `https://cloudbuild.googleapis.com/v1/projects/${project}/locations/${region}/triggers/${trigger}:run`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token.token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ branchName: "main" }),
      }
    );
    if (!res.ok) return { ok: false, error: `Cloud Build ${res.status}: ${(await res.text()).slice(0, 200)}` };
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
