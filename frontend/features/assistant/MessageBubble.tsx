import ReactMarkdown from "react-markdown";

import type { MessageOut } from "@/types/api";

const CONFIDENCE_LABEL: Record<string, string> = {
  high: "High confidence",
  medium: "Medium confidence",
  low: "Low confidence",
};

// Assistant answers naturally come back as Markdown (bold, lists) from the
// LLM; render it properly instead of showing literal ** and - characters.
// react-markdown never renders raw HTML by default, so this is safe even
// though the content is model-generated text grounded in uploaded documents.
const markdownComponents = {
  p: (props: React.ComponentPropsWithoutRef<"p">) => <p className="mb-2 last:mb-0" {...props} />,
  ul: (props: React.ComponentPropsWithoutRef<"ul">) => (
    <ul className="mb-2 list-disc space-y-0.5 pl-5 last:mb-0" {...props} />
  ),
  ol: (props: React.ComponentPropsWithoutRef<"ol">) => (
    <ol className="mb-2 list-decimal space-y-0.5 pl-5 last:mb-0" {...props} />
  ),
  strong: (props: React.ComponentPropsWithoutRef<"strong">) => (
    <strong className="font-semibold" {...props} />
  ),
  code: (props: React.ComponentPropsWithoutRef<"code">) => (
    <code className="rounded bg-black/5 px-1 py-0.5 text-[0.85em] dark:bg-white/10" {...props} />
  ),
  a: (props: React.ComponentPropsWithoutRef<"a">) => (
    <a className="underline" target="_blank" rel="noreferrer" {...props} />
  ),
};

export function MessageBubble({ message }: { message: MessageOut }) {
  const isUser = message.role === "USER";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[75%] rounded-lg px-4 py-2.5 text-sm ${
          isUser
            ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
            : "bg-white text-zinc-900 shadow-sm dark:bg-zinc-900 dark:text-zinc-50"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <ReactMarkdown components={markdownComponents}>{message.content}</ReactMarkdown>
        )}

        {!isUser && message.sources && message.sources.length > 0 ? (
          <div className="mt-3 border-t border-zinc-200 pt-2 dark:border-zinc-700">
            <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              Sources
            </p>
            <ul className="mt-1 space-y-0.5">
              {message.sources.map((source) => (
                <li key={source.chunk_id} className="text-xs text-zinc-500 dark:text-zinc-400">
                  {source.document_title}
                  {source.page !== null ? ` — Page ${source.page}` : ""}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {!isUser && message.confidence && message.confidence !== "none" ? (
          <p className="mt-2 text-[11px] text-zinc-400 dark:text-zinc-500">
            {CONFIDENCE_LABEL[message.confidence] ?? message.confidence}
          </p>
        ) : null}
      </div>
    </div>
  );
}
