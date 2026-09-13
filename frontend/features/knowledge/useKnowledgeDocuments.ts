"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/features/auth/AuthContext";
import { listDocuments } from "@/features/knowledge/api";
import type { KnowledgeDocumentPublic } from "@/types/api";

const POLL_INTERVAL_MS = 3000;
const IN_FLIGHT_STATUSES = new Set(["UPLOADING", "PROCESSING", "INDEXING"]);

/** Fetches every document the caller can see (no server-side filtering — at
 * this scale the /knowledge page filters client-side, which also avoids the
 * category dropdown shrinking to only whatever's currently filtered). While
 * any document is still processing, polls every few seconds so status
 * changes show up live without a manual refresh. */
export function useKnowledgeDocuments() {
  const { accessToken } = useAuth();
  const [documents, setDocuments] = useState<KnowledgeDocumentPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    if (!accessToken) return;
    listDocuments(accessToken)
      .then((data) => {
        setDocuments(data);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load documents.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [accessToken]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const hasInFlight = documents.some((doc) => IN_FLIGHT_STATUSES.has(doc.status));
    if (!hasInFlight) return;
    const interval = setInterval(refresh, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [documents, refresh]);

  return { documents, loading, error, refresh };
}
