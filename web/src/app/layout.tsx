import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

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

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-zinc-950 text-zinc-100 antialiased">
        <div className="mx-auto max-w-5xl px-4">
          <header className="flex items-center gap-6 border-b border-zinc-800 py-4">
            <span className="font-semibold text-emerald-400">stocks-analyzer</span>
            <nav className="flex gap-4 text-sm text-zinc-400">
              {nav.map((n) => (
                <Link key={n.href} href={n.href} className="hover:text-zinc-100">
                  {n.label}
                </Link>
              ))}
            </nav>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
