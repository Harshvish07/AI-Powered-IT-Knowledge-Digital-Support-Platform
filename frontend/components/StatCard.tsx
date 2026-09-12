interface StatCardProps {
  title: string;
  value: string;
  description?: string;
}

export function StatCard({ title, value, description }: StatCardProps) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">{title}</p>
      <p className="mt-2 text-2xl font-semibold text-zinc-900 dark:text-zinc-50">{value}</p>
      {description ? (
        <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">{description}</p>
      ) : null}
    </div>
  );
}
