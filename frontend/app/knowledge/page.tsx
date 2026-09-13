"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { NavBar } from "@/components/NavBar";
import { DocumentCard } from "@/features/knowledge/DocumentCard";
import { useKnowledgeDocuments } from "@/features/knowledge/useKnowledgeDocuments";
import { useRequireAuth } from "@/features/auth/useRequireAuth";

export default function KnowledgePage() {
  const { status, user } = useRequireAuth();
  const isAdmin = user?.role === "ADMIN";
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");

  const { documents, loading, error, refresh } = useKnowledgeDocuments();

  const categories = useMemo(
    () => Array.from(new Set(documents.map((doc) => doc.category))).sort(),
    [documents],
  );

  const filteredDocuments = useMemo(() => {
    const query = search.trim().toLowerCase();
    return documents.filter((doc) => {
      if (category && doc.category !== category) return false;
      if (!query) return true;
      return (
        doc.title.toLowerCase().includes(query) ||
        (doc.description ?? "").toLowerCase().includes(query) ||
        doc.category.toLowerCase().includes(query)
      );
    });
  }, [documents, category, search]);

  if (status !== "authenticated") {
    return (
      <div className="flex flex-1 items-center justify-center bg-zinc-50 dark:bg-black">
        <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 dark:bg-black">
      <NavBar />

      <header className="border-b border-zinc-200 bg-white px-8 py-6 dark:border-zinc-800 dark:bg-zinc-950">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
              Knowledge Base
            </h1>
            <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
              IT guides, procedures, and policies
            </p>
          </div>
          {isAdmin ? (
            <Link
              href="/knowledge/upload"
              className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-semibold text-white dark:bg-zinc-100 dark:text-zinc-900"
            >
              Upload document
            </Link>
          ) : null}
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-8 py-10">
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="search"
            placeholder="Search documents..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="w-64 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
          />
          <select
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
          >
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-6">
          {loading ? (
            <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading documents...</p>
          ) : error ? (
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          ) : filteredDocuments.length === 0 ? (
            <p className="text-sm text-zinc-500 dark:text-zinc-400">No documents found.</p>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {filteredDocuments.map((doc) => (
                <DocumentCard key={doc.id} document={doc} onChanged={refresh} />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
