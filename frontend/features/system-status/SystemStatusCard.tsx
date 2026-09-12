"use client";

import { useHealthStatus } from "@/hooks/useHealthStatus";

export function SystemStatusCard() {
  const health = useHealthStatus();

  const label =
    health.status === "loading"
      ? "Checking..."
      : health.status === "online"
        ? `Online (${health.data.status})`
        : "Offline";

  const dotColor =
    health.status === "online"
      ? "bg-green-500"
      : health.status === "loading"
        ? "bg-yellow-500"
        : "bg-red-500";

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">Backend API</p>
      <div className="mt-2 flex items-center gap-2">
        <span className={`h-2.5 w-2.5 rounded-full ${dotColor}`} />
        <span className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">{label}</span>
      </div>
      <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">GET /health</p>
    </div>
  );
}
