"use client";

import { StatCard } from "@/components/StatCard";
import { AdminLayout } from "@/features/admin/AdminLayout";
import { BarChart } from "@/features/admin/BarChart";
import { Sparkline } from "@/features/admin/Sparkline";
import { useDashboardMetrics } from "@/features/admin/useDashboardMetrics";
import { useRequireAuth } from "@/features/auth/useRequireAuth";

const CATEGORY_LABELS: Record<string, string> = {
  HARDWARE: "Hardware",
  SOFTWARE: "Software",
  NETWORK: "Network",
  ACCOUNT_ACCESS: "Account Access",
  SECURITY: "Security",
  OTHER: "Other",
};

const STATUS_LABELS: Record<string, string> = {
  OPEN: "Open",
  IN_PROGRESS: "In Progress",
  RESOLVED: "Resolved",
  CLOSED: "Closed",
};

export default function AdminDashboardPage() {
  const { status, user } = useRequireAuth({ role: "ADMIN" });
  const { metrics, loading, error } = useDashboardMetrics();

  if (status !== "authenticated" || user?.role !== "ADMIN") {
    return (
      <div className="flex flex-1 items-center justify-center bg-zinc-50 dark:bg-black">
        <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading...</p>
      </div>
    );
  }

  return (
    <AdminLayout title="Admin Dashboard" description="Live metrics across the platform">
      {loading ? (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading metrics...</p>
      ) : error ? (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      ) : !metrics ? (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">No metrics available.</p>
      ) : (
        <div className="space-y-8">
          <section>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              Users
            </h2>
            <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <StatCard title="Total users" value={String(metrics.total_users)} />
              <StatCard title="Active users" value={String(metrics.active_users)} />
            </div>
          </section>

          <section>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              Knowledge base
            </h2>
            <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <StatCard title="Total documents" value={String(metrics.total_documents)} />
              <StatCard title="Ready" value={String(metrics.ready_documents)} />
              <StatCard title="Failed" value={String(metrics.failed_documents)} />
            </div>
          </section>

          <section>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              Tickets
            </h2>
            <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard title="Total tickets" value={String(metrics.total_tickets)} />
              <StatCard title="Open" value={String(metrics.open_tickets)} />
              <StatCard title="In progress" value={String(metrics.in_progress_tickets)} />
              <StatCard title="Resolved" value={String(metrics.resolved_tickets)} />
            </div>
          </section>

          <section>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              AI assistant
            </h2>
            <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <StatCard title="Questions asked" value={String(metrics.ai_questions)} />
            </div>
          </section>

          <section>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              Charts
            </h2>
            <div className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-2">
              <BarChart
                title="Tickets by status"
                items={Object.entries(metrics.tickets_by_status).map(([key, value]) => ({
                  label: STATUS_LABELS[key] ?? key,
                  value,
                }))}
              />
              <BarChart
                title="Tickets by category"
                items={Object.entries(metrics.tickets_by_category).map(([key, value]) => ({
                  label: CATEGORY_LABELS[key] ?? key,
                  value,
                }))}
              />
              <div className="lg:col-span-2">
                <Sparkline title="AI questions over time" data={metrics.ai_questions_by_day} />
              </div>
            </div>
          </section>
        </div>
      )}
    </AdminLayout>
  );
}
