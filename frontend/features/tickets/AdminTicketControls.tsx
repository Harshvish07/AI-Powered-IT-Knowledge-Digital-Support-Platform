"use client";

import { useEffect, useState } from "react";

import { listUsers } from "@/features/auth/api";
import { useAuth } from "@/features/auth/AuthContext";
import { assignTicket, updateTicket } from "@/features/tickets/api";
import type { TicketDetail, TicketPriority, TicketStatus, UserPublic } from "@/types/api";

const STATUSES: TicketStatus[] = ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"];
const PRIORITIES: TicketPriority[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

interface AdminTicketControlsProps {
  ticket: TicketDetail;
  onUpdated: (ticket: TicketDetail) => void;
}

export function AdminTicketControls({ ticket, onUpdated }: AdminTicketControlsProps) {
  const { accessToken } = useAuth();
  const [users, setUsers] = useState<UserPublic[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    listUsers(accessToken)
      .then(setUsers)
      .catch(() => {
        // Assignment dropdown just stays empty; not fatal for viewing the ticket.
      });
  }, [accessToken]);

  async function handleStatusChange(status: TicketStatus) {
    if (!accessToken) return;
    setBusy(true);
    setError(null);
    try {
      onUpdated(await updateTicket(accessToken, ticket.id, { status }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update status.");
    } finally {
      setBusy(false);
    }
  }

  async function handlePriorityChange(priority: TicketPriority) {
    if (!accessToken) return;
    setBusy(true);
    setError(null);
    try {
      onUpdated(await updateTicket(accessToken, ticket.id, { priority }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update priority.");
    } finally {
      setBusy(false);
    }
  }

  async function handleAssignChange(assignedTo: string) {
    if (!accessToken) return;
    setBusy(true);
    setError(null);
    try {
      onUpdated(await assignTicket(accessToken, ticket.id, assignedTo || null));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to assign ticket.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-6 grid grid-cols-1 gap-4 border-t border-zinc-100 pt-6 sm:grid-cols-3 dark:border-zinc-800">
      <div>
        <label className="block text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          Status
        </label>
        <select
          value={ticket.status}
          disabled={busy}
          onChange={(event) => handleStatusChange(event.target.value as TicketStatus)}
          className="mt-1 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
        >
          {STATUSES.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          Priority
        </label>
        <select
          value={ticket.priority}
          disabled={busy}
          onChange={(event) => handlePriorityChange(event.target.value as TicketPriority)}
          className="mt-1 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
        >
          {PRIORITIES.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          Assigned to
        </label>
        <select
          value={ticket.assigned_to ?? ""}
          disabled={busy}
          onChange={(event) => handleAssignChange(event.target.value)}
          className="mt-1 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
        >
          <option value="">Unassigned</option>
          {users.map((option) => (
            <option key={option.id} value={option.id}>
              {option.full_name} ({option.role})
            </option>
          ))}
        </select>
      </div>

      {error ? (
        <p className="text-sm text-red-600 sm:col-span-3 dark:text-red-400">{error}</p>
      ) : null}
    </div>
  );
}
