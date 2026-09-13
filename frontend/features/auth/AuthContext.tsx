"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import {
  getMe,
  loginRequest,
  logoutRequest,
  refreshRequest,
  registerRequest,
} from "@/features/auth/api";
import type { UserPublic } from "@/types/api";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  status: AuthStatus;
  user: UserPublic | null;
  accessToken: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<UserPublic | null>(null);
  // Kept in memory only (never localStorage) to limit exposure if a script on
  // the page is ever compromised; the refresh token lives in an httpOnly
  // cookie the backend sets, which JS can't read at all.
  const [accessToken, setAccessToken] = useState<string | null>(null);

  const applyAccessToken = useCallback(async (token: string) => {
    const me = await getMe(token);
    setAccessToken(token);
    setUser(me);
    setStatus("authenticated");
  }, []);

  useEffect(() => {
    let cancelled = false;
    refreshRequest()
      .then(async (tokenResponse) => {
        if (cancelled) return;
        await applyAccessToken(tokenResponse.access_token);
      })
      .catch(() => {
        if (!cancelled) setStatus("unauthenticated");
      });
    return () => {
      cancelled = true;
    };
  }, [applyAccessToken]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokenResponse = await loginRequest(email, password);
      await applyAccessToken(tokenResponse.access_token);
    },
    [applyAccessToken],
  );

  const register = useCallback(
    async (email: string, password: string, fullName: string) => {
      const tokenResponse = await registerRequest(email, password, fullName);
      await applyAccessToken(tokenResponse.access_token);
    },
    [applyAccessToken],
  );

  const logout = useCallback(async () => {
    try {
      await logoutRequest(accessToken);
    } finally {
      setAccessToken(null);
      setUser(null);
      setStatus("unauthenticated");
    }
  }, [accessToken]);

  const value = useMemo(
    () => ({ status, user, accessToken, login, register, logout }),
    [status, user, accessToken, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
