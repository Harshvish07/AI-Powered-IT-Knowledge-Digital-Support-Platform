"use client";

import { NavBar } from "@/components/NavBar";
import { useRequireAuth } from "@/features/auth/useRequireAuth";

export default function AdminPage() {
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
      <main className="mx-auto w-full max-w-5xl flex-1 px-8 py-10">
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Admin</h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-500 dark:text-zinc-400">
          User management and other admin tooling arrive in a later phase. This page exists to
          demonstrate role-based access control: only a signed-in user with the{" "}
          <code className="rounded bg-zinc-100 px-1 py-0.5 dark:bg-zinc-800">ADMIN</code> role can
          reach it — both here (route-level redirect) and on the backend (
          <code className="rounded bg-zinc-100 px-1 py-0.5 dark:bg-zinc-800">GET /api/users</code>{" "}
          returns 403 for anyone else).
        </p>
      </main>
    </div>
  );
}
