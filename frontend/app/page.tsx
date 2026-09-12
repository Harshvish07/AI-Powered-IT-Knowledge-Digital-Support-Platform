import { ModulePlaceholderCard } from "@/components/ModulePlaceholderCard";
import { StatCard } from "@/components/StatCard";
import { SystemStatusCard } from "@/features/system-status/SystemStatusCard";

export default function DashboardPage() {
  return (
    <div className="flex flex-1 flex-col bg-zinc-50 dark:bg-black">
      <header className="border-b border-zinc-200 bg-white px-8 py-6 dark:border-zinc-800 dark:bg-zinc-950">
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
          AI-Powered IT Knowledge &amp; Digital Support Platform
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Project foundation — dashboard placeholder
        </p>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-8 py-10">
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <SystemStatusCard />
          <StatCard title="Environment" value="Development" />
          <StatCard title="Phase" value="1 / 9" description="Project foundation" />
        </section>

        <section className="mt-10">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            Upcoming modules
          </h2>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <ModulePlaceholderCard
              title="Knowledge Base"
              description="Searchable IT knowledge articles and documentation."
            />
            <ModulePlaceholderCard
              title="Support Tickets"
              description="Create, track, and resolve support requests."
            />
            <ModulePlaceholderCard
              title="AI Assistant"
              description="Retrieval-augmented answers powered by OpenAI."
            />
            <ModulePlaceholderCard
              title="Authentication"
              description="User accounts, roles, and access control."
            />
          </div>
        </section>
      </main>
    </div>
  );
}
