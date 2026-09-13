import type { DocumentStatus } from "@/types/api";

const STATUS_STYLES: Record<DocumentStatus, string> = {
  UPLOADING: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
  PROCESSING: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  INDEXING: "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300",
  READY: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  FAILED: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span
      className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {status}
    </span>
  );
}
