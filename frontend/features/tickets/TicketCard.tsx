import Link from "next/link";

import { PriorityBadge } from "@/features/tickets/PriorityBadge";
import { StatusBadge } from "@/features/tickets/StatusBadge";
import type { TicketPublic } from "@/types/api";

interface TicketCardProps {
  ticket: TicketPublic;
  href: string;
}

export function TicketCard({ ticket, href }: TicketCardProps) {
  return (
    <Link
      href={href}
      className="block rounded-lg border border-zinc-200 bg-white p-5 shadow-sm transition-colors hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-zinc-700"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="font-semibold text-zinc-900 dark:text-zinc-50">{ticket.title}</span>
        <div className="flex shrink-0 items-center gap-2">
          <PriorityBadge priority={ticket.priority} />
          <StatusBadge status={ticket.status} />
        </div>
      </div>
      <p className="mt-1 text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
        {ticket.category.replace("_", " ")}
      </p>
      <p className="mt-2 line-clamp-2 text-sm text-zinc-600 dark:text-zinc-300">
        {ticket.description}
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-zinc-500 dark:text-zinc-400">
        {ticket.created_by_name ? <span>Reported by {ticket.created_by_name}</span> : null}
        <span>
          {ticket.assigned_to_name ? `Assigned to ${ticket.assigned_to_name}` : "Unassigned"}
        </span>
        <span>{new Date(ticket.created_at).toLocaleDateString()}</span>
      </div>
    </Link>
  );
}
