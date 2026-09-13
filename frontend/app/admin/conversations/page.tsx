"use client";

import { useMemo, useState } from "react";

import { AdminLayout } from "@/features/admin/AdminLayout";
import { useAdminConversations } from "@/features/admin/useAdminConversations";
import { useRequireAuth } from "@/features/auth/useRequireAuth";

export default function AdminConversationsPage() {
  const { status, user } = useRequireAuth({ role: "ADMIN" });
  const { conversations, loading, error } = useAdminConversations();
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return conversations;
    return conversations.filter(
      (conversation) =>
        conversation.title.toLowerCase().includes(query) ||
        (conversation.user_name ?? "").toLowerCase().includes(query) ||
        (conversation.user_email ?? "").toLowerCase().includes(query),
    );
  }, [conversations, search]);

  if (status !== "authenticated" || user?.role !== "ADMIN") {
    return (
      <div className="flex flex-1 items-center justify-center bg-zinc-50 dark:bg-black">
        <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading...</p>
      </div>
    );
  }

  return (
    <AdminLayout
      title="AI Conversations"
      description="Metadata only, for support and diagnostic purposes — message content is not shown here"
    >
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="search"
          placeholder="Search by user or title..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="w-64 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
        />
      </div>

      <div className="mt-6 overflow-x-auto rounded-lg border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        {loading ? (
          <p className="p-6 text-sm text-zinc-500 dark:text-zinc-400">Loading conversations...</p>
        ) : error ? (
          <p className="p-6 text-sm text-red-600 dark:text-red-400">{error}</p>
        ) : filtered.length === 0 ? (
          <p className="p-6 text-sm text-zinc-500 dark:text-zinc-400">
            {conversations.length === 0
              ? "No conversations have been started yet."
              : "No conversations match the current search."}
          </p>
        ) : (
          <table className="w-full min-w-140 text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-200 text-xs uppercase tracking-wide text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
                <th className="px-4 py-3 font-medium">User</th>
                <th className="px-4 py-3 font-medium">Title</th>
                <th className="px-4 py-3 font-medium">Messages</th>
                <th className="px-4 py-3 font-medium">Started</th>
                <th className="px-4 py-3 font-medium">Last activity</th>
              </tr>
            </thead>
            <tbody className="[&>tr>td]:px-4">
              {filtered.map((conversation) => (
                <tr
                  key={conversation.id}
                  className="border-b border-zinc-100 last:border-0 dark:border-zinc-800"
                >
                  <td className="py-3">
                    <div className="font-medium text-zinc-900 dark:text-zinc-50">
                      {conversation.user_name ?? "Former user"}
                    </div>
                    <div className="text-xs text-zinc-500 dark:text-zinc-400">
                      {conversation.user_email ?? "—"}
                    </div>
                  </td>
                  <td className="py-3 text-zinc-700 dark:text-zinc-300">{conversation.title}</td>
                  <td className="py-3 text-zinc-700 dark:text-zinc-300">
                    {conversation.message_count}
                  </td>
                  <td className="py-3 text-zinc-500 dark:text-zinc-400">
                    {new Date(conversation.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-3 text-zinc-500 dark:text-zinc-400">
                    {new Date(conversation.updated_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </AdminLayout>
  );
}
