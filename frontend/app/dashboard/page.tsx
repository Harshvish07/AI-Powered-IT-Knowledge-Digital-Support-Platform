"use client";

import Link from "next/link";

import { NavBar } from "@/components/NavBar";
import { StatCard } from "@/components/StatCard";
import { ProfileCard } from "@/features/auth/ProfileCard";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import { SystemStatusCard } from "@/features/system-status/SystemStatusCard";

export default function DashboardPage() {
  const { status } = useRequireAuth();

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
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
          AI-Powered IT Knowledge &amp; Digital Support Platform
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Dashboard</p>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-8 py-10">
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <ProfileCard />
          <SystemStatusCard />
          <StatCard title="Phase" value="8 / 9" description="Production Hardening & Deployment" />
        </section>

        <section className="mt-10">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            Modules
          </h2>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Link
              href="/tickets"
              className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm transition-colors hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-zinc-700"
            >
              <h3 className="font-semibold text-zinc-900 dark:text-zinc-50">Support Tickets</h3>
              <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
                Create, track, and comment on IT support requests.
              </p>
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}
