import "server-only";
import { PostgrestClient } from "@supabase/postgrest-js";

// Thin PostgREST client (no realtime/auth deps — supabase-js's realtime module
// requires Node 22+ native WebSocket and crashes on Node 20 servers).
// Service key: server-side only; RLS has no policies, so the anon key sees nothing.
export function supabase() {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_KEY;
  if (!url || !key) throw new Error("SUPABASE_URL / SUPABASE_SERVICE_KEY not set");
  return new PostgrestClient(`${url}/rest/v1`, {
    headers: { apikey: key, Authorization: `Bearer ${key}` },
  });
}
