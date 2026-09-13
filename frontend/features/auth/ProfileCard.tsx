"use client";

import { useEffect, useState } from "react";

import { getMe } from "@/features/auth/api";
import { useAuth } from "@/features/auth/AuthContext";
import type { UserPublic } from "@/types/api";

/** Fetches the current user's profile live from GET /api/users/me, rather than
 * only reusing the cached value from AuthContext — this is the page's demo of a
 * protected API call using the Bearer access token. */
export function ProfileCard() {
  const { accessToken } = useAuth();
  const [profile, setProfile] = useState<UserPublic | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    let cancelled = false;

    getMe(accessToken)
      .then((data) => {
        if (!cancelled) setProfile(data);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load profile.");
      });

    return () => {
      cancelled = true;
    };
  }, [accessToken]);

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">Signed in as</p>
      {error ? (
        <p className="mt-2 text-sm text-red-600 dark:text-red-400">{error}</p>
      ) : profile ? (
        <>
          <p className="mt-2 text-lg font-semibold text-zinc-900 dark:text-zinc-50">
            {profile.full_name}
          </p>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">{profile.email}</p>
          <span className="mt-2 inline-block rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
            {profile.role}
          </span>
        </>
      ) : (
        <p className="mt-2 text-sm text-zinc-400">Loading...</p>
      )}
      <p className="mt-2 text-xs text-zinc-400">GET /api/users/me</p>
    </div>
  );
}
