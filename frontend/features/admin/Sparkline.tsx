import type { DailyCount } from "@/types/api";

interface SparklineProps {
  title: string;
  data: DailyCount[];
}

const WIDTH = 100;
const HEIGHT = 32;

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function Sparkline({ title, data }: SparklineProps) {
  const total = data.reduce((sum, day) => sum + day.count, 0);
  const max = Math.max(1, ...data.map((day) => day.count));

  const points = data
    .map((day, index) => {
      const x = data.length > 1 ? (index / (data.length - 1)) * WIDTH : 0;
      const y = HEIGHT - (day.count / max) * HEIGHT;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">{title}</h3>
        <span className="text-xs text-zinc-500 dark:text-zinc-400">
          {total} in last {data.length} days
        </span>
      </div>

      {total === 0 ? (
        <p className="mt-6 text-sm text-zinc-500 dark:text-zinc-400">No questions asked yet.</p>
      ) : (
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          preserveAspectRatio="none"
          className="mt-4 h-20 w-full text-zinc-900 dark:text-zinc-100"
        >
          <polyline
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            vectorEffect="non-scaling-stroke"
            points={points}
          />
        </svg>
      )}

      {data.length > 0 ? (
        <div className="mt-2 flex justify-between text-[10px] text-zinc-400 dark:text-zinc-500">
          <span>{formatDate(data[0].date)}</span>
          <span>{formatDate(data[data.length - 1].date)}</span>
        </div>
      ) : null}
    </div>
  );
}
