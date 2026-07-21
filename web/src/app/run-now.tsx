"use client";

import { useState, useTransition } from "react";
import { triggerRun } from "./actions";

export function RunNowButton() {
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<string | null>(null);
  return (
    <span className="flex items-center gap-2">
      <button
        disabled={pending}
        onClick={() =>
          start(async () => {
            const r = await triggerRun();
            setMsg(r.ok ? "Screener started — results in a few minutes." : r.error ?? "Failed");
          })
        }
        className="rounded-md border border-border-ui bg-card px-3 py-1.5 text-sm text-muted hover:text-fg disabled:opacity-50"
      >
        {pending ? "Starting…" : "Run screener now"}
      </button>
      {msg && <span className="text-xs text-faint">{msg}</span>}
    </span>
  );
}
