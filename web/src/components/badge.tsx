import type { Tone } from "@/lib/labels";

const toneClasses: Record<Tone, string> = {
  buy: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300",
  danger: "bg-red-100 text-red-800 dark:bg-red-900/60 dark:text-red-300",
  warn: "bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-300",
  info: "bg-sky-100 text-sky-800 dark:bg-sky-900/60 dark:text-sky-300",
  neutral: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400",
};

export function Badge({
  tone,
  title,
  children,
}: {
  tone: Tone;
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      title={title}
      className={`inline-block whitespace-nowrap rounded px-2 py-0.5 text-xs ${toneClasses[tone]} ${title ? "cursor-help" : ""}`}
    >
      {children}
    </span>
  );
}
