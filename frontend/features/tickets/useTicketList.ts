"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/features/auth/AuthContext";
import { listAllTickets, listMyTickets } from "@/features/tickets/api";
import type { TicketPublic } from "@/types/api";

/** Fetches either the caller's own tickets or, for the admin view, every
 * ticket — filtering (status/category/priority/search) happens client-side
 * over the loaded list, mirroring useKnowledgeDocuments from Phase 3. */
export function useTicketList(scope: "mine" | "all") {
  const { accessToken } = useAuth();
  const [tickets, setTickets] = useState<TicketPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    if (!accessToken) return;
    const request = scope === "mine" ? listMyTickets(accessToken) : listAllTickets(accessToken);
    request
      .then((data) => {
        setTickets(data);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load tickets.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [accessToken, scope]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { tickets, loading, error, refresh };
}
