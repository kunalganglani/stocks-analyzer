import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { createToken, SESSION_COOKIE, timingSafeEqualStr } from "@/lib/auth";

async function login(formData: FormData) {
  "use server";
  const password = String(formData.get("password") ?? "");
  const expected = process.env.ACCESS_PASSWORD;
  const secret = process.env.SESSION_SECRET;
  if (!expected || !secret) throw new Error("auth not configured");
  if (!timingSafeEqualStr(password, expected)) redirect("/login?err=1");
  const jar = await cookies();
  jar.set(SESSION_COOKIE, await createToken(secret), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 30 * 24 * 60 * 60,
    path: "/",
  });
  redirect("/");
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ err?: string }>;
}) {
  const { err } = await searchParams;
  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-950">
      <form action={login} className="w-80 space-y-4 rounded-xl border border-zinc-800 bg-zinc-900 p-8">
        <h1 className="text-lg font-semibold text-zinc-100">stocks-analyzer</h1>
        {err && <p className="text-sm text-red-400">Wrong password.</p>}
        <input
          type="password"
          name="password"
          placeholder="Password"
          autoFocus
          className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-zinc-100 outline-none focus:border-zinc-500"
        />
        <button className="w-full rounded-md bg-emerald-600 py-2 font-medium text-white hover:bg-emerald-500">
          Enter
        </button>
      </form>
    </main>
  );
}
