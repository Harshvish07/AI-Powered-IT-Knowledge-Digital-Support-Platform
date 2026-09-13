"use client";

import { useEffect, useState } from "react";

import { getDashboardMetrics } from "@/features/admin/api";
import { useAuth } from "@/features/auth/AuthContext";
import type { DashboardMetrics } from "@/types/api";

export function useDashboardMetrics() {
  const { accessToken } = useAuth();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    getDashboardMetrics(accessToken)
      .then((data) => {
        setMetrics(data);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load dashboard metrics.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [accessToken]);

  return { metrics, loading, error };
}
