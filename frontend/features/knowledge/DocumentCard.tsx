"use client";

import Link from "next/link";
import { useState } from "react";

import { useAuth } from "@/features/auth/AuthContext";
import { deleteDocument, reindexDocument } from "@/features/knowledge/api";
import { StatusBadge } from "@/features/knowledge/StatusBadge";
import type { KnowledgeDocumentPublic } from "@/types/api";

interface DocumentCardProps {
  document: KnowledgeDocumentPublic;
  onChanged: () => void;
}

export function DocumentCard({ document, onChanged }: DocumentCardProps) {
  const { accessToken, user } = useAuth();
  const isAdmin = user?.role === "ADMIN";
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  async function handleDelete() {
    if (!accessToken) return;
    if (!window.confirm(`Delete "${document.title}"? This cannot be undone.`)) return;
    setBusy(true);
    setActionError(null);
    try {
      await deleteDocument(accessToken, document.id);
      onChanged();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Delete failed.");
      setBusy(false);
    }
  }

  async function handleReindex() {
    if (!accessToken) return;
    setBusy(true);
    setActionError(null);
    try {
      await reindexDocument(accessToken, document.id);
      onChanged();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Re-index failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col justify-between rounded-lg border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div>
        <div className="flex items-start justify-between gap-2">
          <Link
            href={`/knowledge/${document.id}`}
            className="font-semibold text-zinc-900 hover:underline dark:text-zinc-50"
          >
            {document.title}
          </Link>
          <StatusBadge status={document.status} />
        </div>
        <p className="mt-1 text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          {document.category}
        </p>
        {document.description ? (
          <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-300">{document.description}</p>
        ) : null}
      </div>

      {isAdmin ? (
        <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-zinc-100 pt-3 dark:border-zinc-800">
          <button
            type="button"
            onClick={handleReindex}
            disabled={busy}
            className="text-xs font-medium text-zinc-600 hover:text-zinc-900 disabled:opacity-50 dark:text-zinc-400 dark:hover:text-zinc-50"
          >
            Re-index
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={busy}
            className="text-xs font-medium text-red-600 hover:text-red-800 disabled:opacity-50 dark:text-red-400 dark:hover:text-red-300"
          >
            Delete
          </button>
          {actionError ? (
            <span className="text-xs text-red-600 dark:text-red-400">{actionError}</span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
