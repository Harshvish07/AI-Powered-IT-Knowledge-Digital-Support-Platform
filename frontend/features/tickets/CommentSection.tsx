"use client";

import { useState } from "react";

import { useAuth } from "@/features/auth/AuthContext";
import { addComment } from "@/features/tickets/api";
import type { TicketCommentPublic } from "@/types/api";

interface CommentSectionProps {
  ticketId: string;
  comments: TicketCommentPublic[];
  onCommentAdded: (comment: TicketCommentPublic) => void;
}

export function CommentSection({ ticketId, comments, onCommentAdded }: CommentSectionProps) {
  const { accessToken } = useAuth();
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!accessToken) return;
    if (!content.trim()) {
      setError("Comment must not be empty.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const comment = await addComment(accessToken, ticketId, content.trim());
      onCommentAdded(comment);
      setContent("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to post comment.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mt-6 border-t border-zinc-100 pt-6 dark:border-zinc-800">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
        Comments
      </h2>

      {comments.length === 0 ? (
        <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-400">No comments yet.</p>
      ) : (
        <ul className="mt-3 space-y-3">
          {comments.map((comment) => (
            <li
              key={comment.id}
              className="rounded-md border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-950"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-zinc-900 dark:text-zinc-50">
                  {comment.author_name ?? "Former user"}
                </span>
                <span className="text-xs text-zinc-500 dark:text-zinc-400">
                  {new Date(comment.created_at).toLocaleString()}
                </span>
              </div>
              <p className="mt-1 whitespace-pre-wrap text-sm text-zinc-700 dark:text-zinc-300">
                {comment.content}
              </p>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleSubmit} className="mt-4 space-y-2" noValidate>
        <textarea
          rows={3}
          placeholder="Add a comment..."
          value={content}
          onChange={(event) => setContent(event.target.value)}
          className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
        />
        {error ? (
          <p role="alert" className="text-sm text-red-600 dark:text-red-400">
            {error}
          </p>
        ) : null}
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {submitting ? "Posting..." : "Post comment"}
        </button>
      </form>
    </div>
  );
}
