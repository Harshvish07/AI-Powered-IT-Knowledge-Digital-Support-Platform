"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { NavBar } from "@/components/NavBar";
import { useAuth } from "@/features/auth/AuthContext";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import { deleteDocument, getDocument, reindexDocument } from "@/features/knowledge/api";
import { StatusBadge } from "@/features/knowledge/StatusBadge";
import { ApiError } from "@/lib/apiClient";
import type { KnowledgeDocumentDetail } from "@/types/api";

const IN_FLIGHT_STATUSES = new Set(["UPLOADING", "PROCESSING", "INDEXING"]);

export default function KnowledgeDocumentPage() {
  const { status: authStatus, user } = useRequireAuth();
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { accessToken } = useAuth();
  const isAdmin = user?.role === "ADMIN";

  const [document, setDocument] = useState<KnowledgeDocumentDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!accessToken) return;
    getDocument(accessToken, params.id)
      .then((data) => {
        setDocument(data);
        setLoadError(null);
      })
      .catch((err: unknown) => {
        setLoadError(
          err instanceof ApiError && err.status === 404
            ? "Document not found."
            : "Failed to load document.",
        );
      });
  }, [accessToken, params.id]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!document || !IN_FLIGHT_STATUSES.has(document.status)) return;
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [document, load]);

  async function handleDelete() {
    if (!accessToken || !document) return;
    if (!window.confirm(`Delete "${document.title}"? This cannot be undone.`)) return;
    setBusy(true);
    try {
      await deleteDocument(accessToken, document.id);
      router.replace("/knowledge");
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Delete failed.");
      setBusy(false);
    }
  }

  async function handleReindex() {
    if (!accessToken || !document) return;
    setBusy(true);
    setActionError(null);
    try {
      const updated = await reindexDocument(accessToken, document.id);
      setDocument(updated);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Re-index failed.");
    } finally {
      setBusy(false);
    }
  }

  if (authStatus !== "authenticated") {
    return (
      <div className="flex flex-1 items-center justify-center bg-zinc-50 dark:bg-black">
        <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 dark:bg-black">
      <NavBar />
      <main className="mx-auto w-full max-w-3xl flex-1 px-8 py-10">
        <Link
          href="/knowledge"
          className="text-sm text-zinc-500 hover:underline dark:text-zinc-400"
        >
          &larr; Back to Knowledge Base
        </Link>

        {loadError ? (
          <p className="mt-6 text-sm text-red-600 dark:text-red-400">{loadError}</p>
        ) : !document ? (
          <p className="mt-6 text-sm text-zinc-500 dark:text-zinc-400">Loading...</p>
        ) : (
          <div className="mt-4 rounded-lg border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
                {document.title}
              </h1>
              <StatusBadge status={document.status} />
            </div>
            <p className="mt-1 text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              {document.category}
            </p>
            {document.description ? (
              <p className="mt-3 text-sm text-zinc-600 dark:text-zinc-300">
                {document.description}
              </p>
            ) : null}

            <dl className="mt-6 grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
              <div>
                <dt className="text-zinc-500 dark:text-zinc-400">Filename</dt>
                <dd className="text-zinc-900 dark:text-zinc-50">{document.filename}</dd>
              </div>
              <div>
                <dt className="text-zinc-500 dark:text-zinc-400">Version</dt>
                <dd className="text-zinc-900 dark:text-zinc-50">{document.version}</dd>
              </div>
              <div>
                <dt className="text-zinc-500 dark:text-zinc-400">Chunks indexed</dt>
                <dd className="text-zinc-900 dark:text-zinc-50">{document.chunk_count}</dd>
              </div>
              <div>
                <dt className="text-zinc-500 dark:text-zinc-400">Size</dt>
                <dd className="text-zinc-900 dark:text-zinc-50">
                  {(document.file_size_bytes / 1024).toFixed(1)} KB
                </dd>
              </div>
              <div>
                <dt className="text-zinc-500 dark:text-zinc-400">Uploaded</dt>
                <dd className="text-zinc-900 dark:text-zinc-50">
                  {new Date(document.created_at).toLocaleDateString()}
                </dd>
              </div>
              <div>
                <dt className="text-zinc-500 dark:text-zinc-400">Last updated</dt>
                <dd className="text-zinc-900 dark:text-zinc-50">
                  {new Date(document.updated_at).toLocaleDateString()}
                </dd>
              </div>
            </dl>

            {isAdmin && document.status === "FAILED" && document.error_message ? (
              <div className="mt-6 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300">
                <p className="font-medium">Processing error (visible to admins only)</p>
                <p className="mt-1 whitespace-pre-wrap">{document.error_message}</p>
              </div>
            ) : null}

            {isAdmin ? (
              <div className="mt-6 flex flex-wrap items-center gap-4 border-t border-zinc-100 pt-4 dark:border-zinc-800">
                <button
                  type="button"
                  onClick={handleReindex}
                  disabled={busy}
                  className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium text-zinc-700 hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
                >
                  Re-index
                </button>
                <button
                  type="button"
                  onClick={handleDelete}
                  disabled={busy}
                  className="rounded-md border border-red-300 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50 dark:border-red-900/50 dark:text-red-400 dark:hover:bg-red-950/30"
                >
                  Delete
                </button>
                {actionError ? (
                  <span className="text-sm text-red-600 dark:text-red-400">{actionError}</span>
                ) : null}
              </div>
            ) : null}
          </div>
        )}
      </main>
    </div>
  );
}
