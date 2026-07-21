export function Section({
  title,
  tone,
  children,
}: {
  title: React.ReactNode;
  tone?: "red" | "green";
  children: React.ReactNode;
}) {
  const border =
    tone === "red"
      ? "border-red-300 dark:border-red-900"
      : tone === "green"
      ? "border-emerald-300 dark:border-emerald-900"
      : "border-border-ui";
  return (
    <section className={`rounded-xl border ${border} bg-card p-5`}>
      <h2 className="mb-3 font-semibold">{title}</h2>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

export function Row({ children }: { children: React.ReactNode }) {
  return <div className="text-sm text-muted">{children}</div>;
}
