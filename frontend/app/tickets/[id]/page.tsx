"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { NavBar } from "@/components/NavBar";
import { useAuth } from "@/features/auth/AuthContext";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import { getTicket } from "@/features/tickets/api";
import { CommentSection } from "@/features/tickets/CommentSection";
import { PriorityBadge } from "@/features/tickets/PriorityBadge";
import { StatusBadge } from "@/features/tickets/StatusBadge";
import { ApiError } from "@/lib/apiClient";
import type { TicketDetail } from "@/types/api";

export default function TicketDetailPage() {
  const { status: authStatus } = useRequireAuth();
  const params = useParams<{ id: string }>();
  const { accessToken } = useAuth();

  const [ticket, setTicket] = useState<TicketDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!accessToken) return;
    getTicket(accessToken, params.id)
      .then((data) => {
        setTicket(data);
        setLoadError(null);
      })
      .catch((err: unknown) => {
        setLoadError(
          err instanceof ApiError && err.status === 404
            ? "Ticket not found."
            : "Failed to load ticket.",
        );
      });
  }, [accessToken, params.id]);

  useEffect(() => {
    load();
  }, [load]);

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
      <main className="mx-auto w-full max-w-3xl flex-1 px-8 py-10">
        <Link href="/tickets" className="text-sm text-zinc-500 hover:underline dark:text-zinc-400">
          &larr; Back to My Tickets
        </Link>

        {loadError ? (
          <p className="mt-6 text-sm text-red-600 dark:text-red-400">{loadError}</p>
        ) : !ticket ? (
          <p className="mt-6 text-sm text-zinc-500 dark:text-zinc-400">Loading...</p>
        ) : (
          <div className="mt-4 rounded-lg border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
                {ticket.title}
              </h1>
              <div className="flex items-center gap-2">
                <PriorityBadge priority={ticket.priority} />
                <StatusBadge status={ticket.status} />
              </div>
            </div>
            <p className="mt-1 text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              {ticket.category.replace("_", " ")}
            </p>
            <p className="mt-3 whitespace-pre-wrap text-sm text-zinc-600 dark:text-zinc-300">
              {ticket.description}
            </p>

            <dl className="mt-6 grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
              <div>
                <dt className="text-zinc-500 dark:text-zinc-400">Assigned to</dt>
                <dd className="text-zinc-900 dark:text-zinc-50">
                  {ticket.assigned_to_name ?? "Unassigned"}
                </dd>
              </div>
              <div>
                <dt className="text-zinc-500 dark:text-zinc-400">Created</dt>
                <dd className="text-zinc-900 dark:text-zinc-50">
                  {new Date(ticket.created_at).toLocaleString()}
                </dd>
              </div>
              <div>
                <dt className="text-zinc-500 dark:text-zinc-400">Last updated</dt>
                <dd className="text-zinc-900 dark:text-zinc-50">
                  {new Date(ticket.updated_at).toLocaleString()}
                </dd>
              </div>
            </dl>

            <CommentSection
              ticketId={ticket.id}
              comments={ticket.comments}
              onCommentAdded={(comment) =>
                setTicket((current) =>
                  current ? { ...current, comments: [...current.comments, comment] } : current,
                )
              }
            />
          </div>
        )}
      </main>
    </div>
  );
}
