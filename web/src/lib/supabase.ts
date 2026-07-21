import "server-only";
import { createClient } from "@supabase/supabase-js";

// Service key: server-side only. RLS has no policies, so the anon key sees nothing;
// this client bypasses RLS. Never import from client components.
export function supabase() {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_KEY;
  if (!url || !key) throw new Error("SUPABASE_URL / SUPABASE_SERVICE_KEY not set");
  return createClient(url, key, { auth: { persistSession: false } });
}
