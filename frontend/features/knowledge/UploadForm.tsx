"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { useAuth } from "@/features/auth/AuthContext";
import { uploadDocument } from "@/features/knowledge/api";
import { ApiError } from "@/lib/apiClient";

const ACCEPTED_EXTENSIONS = [".pdf", ".txt", ".md", ".markdown"];

export function UploadForm() {
  const { accessToken } = useAuth();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("");
  const [description, setDescription] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function pickFile(selected: File | null) {
    setFile(selected);
    if (selected && !title) {
      setTitle(selected.name.replace(/\.[^.]+$/, ""));
    }
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragActive(false);
    pickFile(event.dataTransfer.files?.[0] ?? null);
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (!file) {
      setError("Choose a file to upload.");
      return;
    }
    if (!accessToken) return;

    setSubmitting(true);
    try {
      const document = await uploadDocument(accessToken, {
        file,
        title: title.trim(),
        category: category.trim(),
        description: description.trim() || undefined,
      });
      router.push(`/knowledge/${document.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-lg space-y-4" noValidate>
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") fileInputRef.current?.click();
        }}
        role="button"
        tabIndex={0}
        aria-label="Choose or drop a file to upload"
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
          dragActive
            ? "border-zinc-500 bg-zinc-100 dark:bg-zinc-800"
            : "border-zinc-300 dark:border-zinc-700"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS.join(",")}
          className="hidden"
          onChange={(event) => pickFile(event.target.files?.[0] ?? null)}
        />
        {file ? (
          <p className="text-sm font-medium text-zinc-900 dark:text-zinc-50">{file.name}</p>
        ) : (
          <>
            <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Drag and drop a file here, or click to browse
            </p>
            <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">PDF, TXT, or Markdown</p>
          </>
        )}
      </div>

      <div>
        <label
          htmlFor="title"
          className="block text-sm font-medium text-zinc-700 dark:text-zinc-300"
        >
          Title
        </label>
        <input
          id="title"
          type="text"
          required
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          className="mt-1 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
        />
      </div>

      <div>
        <label
          htmlFor="category"
          className="block text-sm font-medium text-zinc-700 dark:text-zinc-300"
        >
          Category
        </label>
        <input
          id="category"
          type="text"
          required
          placeholder="e.g. Networking, Security, Policy"
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          className="mt-1 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
        />
      </div>

      <div>
        <label
          htmlFor="description"
          className="block text-sm font-medium text-zinc-700 dark:text-zinc-300"
        >
          Description (optional)
        </label>
        <textarea
          id="description"
          rows={3}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          className="mt-1 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
        />
      </div>

      {error ? (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-md bg-zinc-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
      >
        {submitting ? "Uploading..." : "Upload"}
      </button>
    </form>
  );
}
