"use client";

import { useEffect, useState } from "react";

import { listAdminConversations } from "@/features/admin/api";
import { useAuth } from "@/features/auth/AuthContext";
import type { AdminConversationSummary } from "@/types/api";

export function useAdminConversations() {
  const { accessToken } = useAuth();
  const [conversations, setConversations] = useState<AdminConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    listAdminConversations(accessToken)
      .then((data) => {
        setConversations(data);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load conversations.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [accessToken]);

  return { conversations, loading, error };
}
