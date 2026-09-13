"use client";

import { NavBar } from "@/components/NavBar";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import { UploadForm } from "@/features/knowledge/UploadForm";

export default function UploadKnowledgeDocumentPage() {
  const { status, user } = useRequireAuth({ role: "ADMIN" });

  if (status !== "authenticated" || user?.role !== "ADMIN") {
    return (
      <div className="flex flex-1 items-center justify-center bg-zinc-50 dark:bg-black">
        <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 dark:bg-black">
      <NavBar />
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col items-center px-8 py-10">
        <h1 className="mb-6 self-start text-xl font-semibold text-zinc-900 dark:text-zinc-50">
          Upload document
        </h1>
        <UploadForm />
      </main>
    </div>
  );
}
