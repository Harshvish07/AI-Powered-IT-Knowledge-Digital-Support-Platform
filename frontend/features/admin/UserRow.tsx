"use client";

import { useState } from "react";

import { setUserActive } from "@/features/admin/api";
import { useAuth } from "@/features/auth/AuthContext";
import type { UserPublic } from "@/types/api";

interface UserRowProps {
  targetUser: UserPublic;
  onChanged: () => void;
}

export function UserRow({ targetUser, onChanged }: UserRowProps) {
  const { accessToken, user: currentUser } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isSelf = currentUser?.id === targetUser.id;

  async function handleToggle() {
    if (!accessToken) return;
    const nextActive = !targetUser.is_active;
    if (
      !nextActive &&
      !window.confirm(`Deactivate ${targetUser.full_name}? They will be signed out immediately.`)
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await setUserActive(accessToken, targetUser.id, nextActive);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update user.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <tr className="border-b border-zinc-100 last:border-0 dark:border-zinc-800">
      <td className="py-3 pr-4">
        <div className="font-medium text-zinc-900 dark:text-zinc-50">
          {targetUser.full_name}
          {isSelf ? (
            <span className="ml-2 text-xs font-normal text-zinc-400 dark:text-zinc-500">(you)</span>
          ) : null}
        </div>
        <div className="text-xs text-zinc-500 dark:text-zinc-400">{targetUser.email}</div>
      </td>
      <td className="py-3 pr-4">
        <span
          className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${
            targetUser.role === "ADMIN"
              ? "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300"
              : "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
          }`}
        >
          {targetUser.role}
        </span>
      </td>
      <td className="py-3 pr-4">
        <span
          className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${
            targetUser.is_active
              ? "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300"
              : "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"
          }`}
        >
          {targetUser.is_active ? "Active" : "Inactive"}
        </span>
      </td>
      <td className="py-3 pr-4 text-sm text-zinc-500 dark:text-zinc-400">
        {new Date(targetUser.created_at).toLocaleDateString()}
      </td>
      <td className="py-3 text-right">
        {isSelf ? (
          <span className="text-xs text-zinc-400 dark:text-zinc-500">Cannot modify self</span>
        ) : (
          <button
            type="button"
            onClick={handleToggle}
            disabled={busy}
            className={`rounded-md border px-3 py-1.5 text-xs font-medium disabled:opacity-50 ${
              targetUser.is_active
                ? "border-red-300 text-red-600 hover:bg-red-50 dark:border-red-900/50 dark:text-red-400 dark:hover:bg-red-950/30"
                : "border-green-300 text-green-700 hover:bg-green-50 dark:border-green-900/50 dark:text-green-400 dark:hover:bg-green-950/30"
            }`}
          >
            {targetUser.is_active ? "Deactivate" : "Activate"}
          </button>
        )}
        {error ? <p className="mt-1 text-xs text-red-600 dark:text-red-400">{error}</p> : null}
      </td>
    </tr>
  );
}
