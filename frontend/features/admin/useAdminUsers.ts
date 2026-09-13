"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/features/auth/AuthContext";
import { listUsers } from "@/features/auth/api";
import type { UserPublic } from "@/types/api";

export function useAdminUsers() {
  const { accessToken } = useAuth();
  const [users, setUsers] = useState<UserPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    if (!accessToken) return;
    listUsers(accessToken)
      .then((data) => {
        setUsers(data);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load users.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [accessToken]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { users, loading, error, refresh };
}
