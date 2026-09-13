"use client";

import { useEffect, useRef } from "react";

import { NavBar } from "@/components/NavBar";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import { ChatInput } from "@/features/assistant/ChatInput";
import { ConversationSidebar } from "@/features/assistant/ConversationSidebar";
import { MessageBubble } from "@/features/assistant/MessageBubble";
import { useAssistantChat } from "@/features/assistant/useAssistantChat";

export default function AssistantPage() {
  const { status } = useRequireAuth();
  const chat = useAssistantChat();
  const scrollAnchorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat.messages, chat.sending]);

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
      <div className="flex min-h-0 flex-1">
        <ConversationSidebar
          conversations={chat.conversations}
          activeConversationId={chat.activeConversationId}
          loading={chat.loadingConversations}
          onSelect={chat.loadConversation}
          onNew={chat.startNewConversation}
          onDelete={chat.removeConversation}
        />

        <div className="flex min-h-0 flex-1 flex-col">
          <div className="flex-1 overflow-y-auto px-6 py-6">
            {chat.loadingMessages ? (
              <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading conversation...</p>
            ) : chat.messages.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
                  IT Assistant
                </h2>
                <p className="mt-2 max-w-sm text-sm text-zinc-500 dark:text-zinc-400">
                  Ask a question about company IT policies and procedures — for example, &quot;How
                  do I reset my VPN password?&quot; Answers are grounded in the knowledge base and
                  cite their sources.
                </p>
              </div>
            ) : (
              <div className="mx-auto flex max-w-2xl flex-col gap-4">
                {chat.messages.map((message) => (
                  <MessageBubble key={message.id} message={message} />
                ))}

                {chat.sending ? (
                  <div className="flex justify-start">
                    <div className="rounded-lg bg-white px-4 py-2.5 text-sm text-zinc-400 shadow-sm dark:bg-zinc-900 dark:text-zinc-500">
                      Thinking...
                    </div>
                  </div>
                ) : null}

                {chat.error ? (
                  <div className="flex flex-col items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300">
                    <span>{chat.error}</span>
                    <button
                      type="button"
                      onClick={chat.retry}
                      className="text-xs font-semibold underline"
                    >
                      Retry
                    </button>
                  </div>
                ) : null}

                <div ref={scrollAnchorRef} />
              </div>
            )}
          </div>

          <div className="mx-auto w-full max-w-2xl">
            <ChatInput onSend={chat.sendMessage} disabled={chat.sending} />
          </div>
        </div>
      </div>
    </div>
  );
}
