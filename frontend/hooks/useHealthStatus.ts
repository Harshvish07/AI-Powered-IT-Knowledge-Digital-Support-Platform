"use client";

import { useEffect, useState } from "react";

import { API_BASE_URL } from "@/lib/config";
import type { HealthResponse } from "@/types/api";

type HealthState =
  { status: "loading" } | { status: "online"; data: HealthResponse } | { status: "offline" };

export function useHealthStatus(): HealthState {
  const [state, setState] = useState<HealthState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    fetch(`${API_BASE_URL}/health`)
      .then((res) => {
        if (!res.ok) throw new Error("Health check failed");
        return res.json() as Promise<HealthResponse>;
      })
      .then((data) => {
        if (!cancelled) setState({ status: "online", data });
      })
      .catch(() => {
        if (!cancelled) setState({ status: "offline" });
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
