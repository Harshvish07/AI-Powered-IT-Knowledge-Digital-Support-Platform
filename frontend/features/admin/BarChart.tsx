interface BarChartItem {
  label: string;
  value: number;
}

interface BarChartProps {
  title: string;
  items: BarChartItem[];
}

export function BarChart({ title, items }: BarChartProps) {
  const max = Math.max(1, ...items.map((item) => item.value));

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">{title}</h3>
      <div className="mt-4 space-y-3">
        {items.map((item) => (
          <div key={item.label}>
            <div className="flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400">
              <span>{item.label}</span>
              <span className="font-medium text-zinc-900 dark:text-zinc-50">{item.value}</span>
            </div>
            <div className="mt-1 h-2 w-full rounded-full bg-zinc-100 dark:bg-zinc-800">
              <div
                className="h-2 rounded-full bg-zinc-900 dark:bg-zinc-100"
                style={{ width: `${(item.value / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
