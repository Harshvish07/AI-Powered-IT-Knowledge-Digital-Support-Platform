"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { NavBar } from "@/components/NavBar";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import { TicketCard } from "@/features/tickets/TicketCard";
import { useTicketList } from "@/features/tickets/useTicketList";
import type { TicketPriority, TicketStatus } from "@/types/api";

const STATUSES: TicketStatus[] = ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"];
const PRIORITIES: TicketPriority[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

export default function TicketsPage() {
  const { status: authStatus } = useRequireAuth();
  const [statusFilter, setStatusFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");

  const { tickets, loading, error } = useTicketList("mine");

  const categories = useMemo(
    () => Array.from(new Set(tickets.map((t) => t.category))).sort(),
    [tickets],
  );

  const filteredTickets = useMemo(() => {
    return tickets.filter((ticket) => {
      if (statusFilter && ticket.status !== statusFilter) return false;
      if (categoryFilter && ticket.category !== categoryFilter) return false;
      if (priorityFilter && ticket.priority !== priorityFilter) return false;
      return true;
    });
  }, [tickets, statusFilter, categoryFilter, priorityFilter]);

  if (authStatus !== "authenticated") {
    return (
      <div className="flex flex-1 items-center justify-center bg-zinc-50 dark:bg-black">
        <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 dark:bg-black">
      <NavBar />

      <header className="border-b border-zinc-200 bg-white px-8 py-6 dark:border-zinc-800 dark:bg-zinc-950">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">My Tickets</h1>
            <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
              Support requests you&apos;ve submitted
            </p>
          </div>
          <Link
            href="/tickets/new"
            className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-semibold text-white dark:bg-zinc-100 dark:text-zinc-900"
          >
            New ticket
          </Link>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-8 py-10">
        <div className="flex flex-wrap items-center gap-3">
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
              {tickets.length === 0
                ? "You haven't created any tickets yet."
                : "No tickets match the selected filters."}
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {filteredTickets.map((ticket) => (
                <TicketCard key={ticket.id} ticket={ticket} href={`/tickets/${ticket.id}`} />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
