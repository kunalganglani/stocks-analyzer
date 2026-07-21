// Single-user session tokens: `${exp}.${hmacSHA256(exp, SESSION_SECRET)}`.
// Web Crypto only, so the same code runs in middleware (edge) and server actions.

const encoder = new TextEncoder();

async function hmac(payload: string, secret: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, encoder.encode(payload));
  return Array.from(new Uint8Array(sig)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

export const SESSION_COOKIE = "sa_session";
const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;

export async function createToken(secret: string): Promise<string> {
  const exp = Date.now() + THIRTY_DAYS_MS;
  return `${exp}.${await hmac(String(exp), secret)}`;
}

export async function verifyToken(token: string | undefined, secret: string): Promise<boolean> {
  if (!token) return false;
  const [exp, sig] = token.split(".");
  if (!exp || !sig || Number(exp) < Date.now()) return false;
  const expected = await hmac(exp, secret);
  if (sig.length !== expected.length) return false;
  let diff = 0;
  for (let i = 0; i < sig.length; i++) diff |= sig.charCodeAt(i) ^ expected.charCodeAt(i);
  return diff === 0;
}

export function timingSafeEqualStr(a: string, b: string): boolean {
  const pad = Math.max(a.length, b.length);
  let diff = a.length === b.length ? 0 : 1;
  for (let i = 0; i < pad; i++) diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  return diff === 0;
}
