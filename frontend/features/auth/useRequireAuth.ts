"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/features/auth/AuthContext";
import type { UserRole } from "@/types/api";

interface RequireAuthOptions {
  /** If set, users whose role doesn't match are redirected away (RBAC on the frontend
   * route). The backend still enforces this independently on every API call. */
  role?: UserRole;
  redirectTo?: string;
}

export function useRequireAuth(options?: RequireAuthOptions) {
  const { status, user } = useAuth();
  const router = useRouter();
  const requiredRole = options?.role;
  const redirectTo = options?.redirectTo ?? "/dashboard";

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
      return;
    }
    if (status === "authenticated" && requiredRole && user?.role !== requiredRole) {
      router.replace(redirectTo);
    }
  }, [status, user, requiredRole, redirectTo, router]);

  return { status, user };
}
