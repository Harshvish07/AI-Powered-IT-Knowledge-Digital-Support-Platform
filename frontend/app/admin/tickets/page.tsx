"use client";

import { useMemo, useState } from "react";

import { AdminLayout } from "@/features/admin/AdminLayout";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import { TicketCard } from "@/features/tickets/TicketCard";
import { useTicketList } from "@/features/tickets/useTicketList";
import type { TicketPriority, TicketStatus } from "@/types/api";

const STATUSES: TicketStatus[] = ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"];
const PRIORITIES: TicketPriority[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

export default function AdminTicketsPage() {
  const { status: authStatus, user } = useRequireAuth({ role: "ADMIN" });
  const [statusFilter, setStatusFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [search, setSearch] = useState("");

  const { tickets, loading, error } = useTicketList("all");

  const categories = useMemo(
    () => Array.from(new Set(tickets.map((t) => t.category))).sort(),
    [tickets],
  );

  const filteredTickets = useMemo(() => {
    const query = search.trim().toLowerCase();
    return tickets.filter((ticket) => {
      if (statusFilter && ticket.status !== statusFilter) return false;
      if (categoryFilter && ticket.category !== categoryFilter) return false;
      if (priorityFilter && ticket.priority !== priorityFilter) return false;
      if (!query) return true;
      return (
        ticket.title.toLowerCase().includes(query) ||
        ticket.description.toLowerCase().includes(query)
      );
    });
  }, [tickets, statusFilter, categoryFilter, priorityFilter, search]);

  if (authStatus !== "authenticated" || user?.role !== "ADMIN") {
    return (
      <div className="flex flex-1 items-center justify-center bg-zinc-50 dark:bg-black">
        <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading...</p>
      </div>
    );
  }

  return (
    <AdminLayout title="All Tickets" description="Every support ticket across the organization">
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="search"
            placeholder="Search tickets..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="w-64 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
          />
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
          >
            <option value="">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select
            value={categoryFilter}
            onChange={(event) => setCategoryFilter(event.target.value)}
            className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
          >
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c.replace("_", " ")}
              </option>
            ))}
          </select>
          <select
            value={priorityFilter}
            onChange={(event) => setPriorityFilter(event.target.value)}
            className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
          >
            <option value="">All priorities</option>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-6">
          {loading ? (
            <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading tickets...</p>
          ) : error ? (
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          ) : filteredTickets.length === 0 ? (
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              {tickets.length === 0 ? "No tickets have been submitted yet." : "No tickets match."}
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {filteredTickets.map((ticket) => (
                <TicketCard key={ticket.id} ticket={ticket} href={`/admin/tickets/${ticket.id}`} />
              ))}
            </div>
          )}
        </div>
      </div>
    </AdminLayout>
  );
}
