interface ModulePlaceholderCardProps {
  title: string;
  description: string;
}

export function ModulePlaceholderCard({ title, description }: ModulePlaceholderCardProps) {
  return (
    <div className="rounded-lg border border-dashed border-zinc-300 p-5 dark:border-zinc-700">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">{title}</h3>
        <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
          Coming soon
        </span>
      </div>
      <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">{description}</p>
    </div>
  );
}
