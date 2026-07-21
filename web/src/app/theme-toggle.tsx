"use client";

// `initial` comes from the server-read cookie so SSR markup and first client
// render agree (no hydration mismatch). Icon swap is pure CSS via dark:.
export function ThemeToggle({ initial }: { initial: "light" | "dark" }) {
  function toggle() {
    const el = document.documentElement;
    const next = el.classList.contains("dark") ? "light" : "dark";
    el.classList.toggle("dark", next === "dark");
    document.cookie = `sa_theme=${next}; path=/; max-age=31536000; samesite=lax`;
  }
  return (
    <button
      onClick={toggle}
      aria-label={`Switch theme (currently ${initial})`}
      title="Switch between dark and light mode"
      className="ml-auto rounded-md border border-border-ui p-2 text-muted hover:text-fg"
    >
      {/* sun — shown in dark mode (click to go light) */}
      <svg className="hidden size-4 dark:block" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4m11.4-11.4 1.4-1.4" />
      </svg>
      {/* moon — shown in light mode (click to go dark) */}
      <svg className="size-4 dark:hidden" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
      </svg>
    </button>
  );
}
