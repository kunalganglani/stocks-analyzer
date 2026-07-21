import type { Metadata } from "next";
import { cookies } from "next/headers";
import Link from "next/link";
import "./globals.css";
import { ThemeToggle } from "./theme-toggle";

export const metadata: Metadata = {
  title: "stocks-analyzer",
  description: "Minervini x Buffett/Munger stock signals",
};

const nav = [
  { href: "/", label: "Dashboard" },
  { href: "/screener", label: "Screener" },
  { href: "/positions", label: "Positions" },
  { href: "/signals", label: "Signals" },
];

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const theme =
    (await cookies()).get("sa_theme")?.value === "light" ? ("light" as const) : ("dark" as const);
  return (
    <html lang="en" className={theme === "dark" ? "dark" : undefined}>
      <body className="min-h-screen antialiased">
        <div className="mx-auto max-w-5xl px-4">
          <header className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-border-soft py-4">
            <span className="font-semibold text-emerald-600 dark:text-emerald-400">
              stocks-analyzer
            </span>
            <nav className="flex gap-4 text-sm text-muted">
              {nav.map((n) => (
                <Link key={n.href} href={n.href} className="hover:text-fg">
                  {n.label}
                </Link>
              ))}
            </nav>
            <ThemeToggle initial={theme} />
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
