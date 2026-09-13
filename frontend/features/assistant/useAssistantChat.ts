"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/features/auth/AuthContext";
import {
  deleteConversation,
  getConversation,
  listConversations,
  sendChatMessage,
} from "@/features/assistant/api";
import type { ConversationSummary, MessageOut } from "@/types/api";

let localIdCounter = 0;
function localId(prefix: string): string {
  localIdCounter += 1;
  return `${prefix}-${localIdCounter}`;
}

export function useAssistantChat() {
  const { accessToken } = useAuth();
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageOut[]>([]);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastFailedMessage, setLastFailedMessage] = useState<string | null>(null);

  const refreshConversations = useCallback(() => {
    if (!accessToken) return;
    listConversations(accessToken)
      .then((data) => setConversations(data))
      .catch(() => {
        // A failed list refresh isn't fatal to the active chat — leave the
        // previous list in place rather than surfacing a disruptive error.
      })
      .finally(() => setLoadingConversations(false));
  }, [accessToken]);

  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  const loadConversation = useCallback(
    (id: string) => {
      if (!accessToken) return;
      setActiveConversationId(id);
      setLoadingMessages(true);
      setError(null);
      getConversation(accessToken, id)
        .then((data) => setMessages(data.messages))
        .catch(() => setError("Failed to load that conversation."))
        .finally(() => setLoadingMessages(false));
    },
    [accessToken],
  );

  const startNewConversation = useCallback(() => {
    setActiveConversationId(null);
    setMessages([]);
    setError(null);
    setLastFailedMessage(null);
  }, []);

  const sendMessage = useCallback(
    (text: string) => {
      if (!accessToken || !text.trim()) return;
      setSending(true);
      setError(null);
      setLastFailedMessage(null);

      setMessages((prev) => [
        ...prev,
        {
          id: localId("pending-user"),
          role: "USER",
          content: text,
          sources: null,
          confidence: null,
          created_at: new Date().toISOString(),
        },
      ]);

      sendChatMessage(accessToken, text, activeConversationId)
        .then((response) => {
          setActiveConversationId(response.conversation_id);
          setMessages((prev) => [
            ...prev,
            {
              id: localId("pending-assistant"),
              role: "ASSISTANT",
              content: response.answer,
              sources: response.sources,
              confidence: response.confidence,
              created_at: new Date().toISOString(),
            },
          ]);
          refreshConversations();
        })
        .catch((err: unknown) => {
          setError(err instanceof Error ? err.message : "Failed to get a response.");
          setLastFailedMessage(text);
        })
        .finally(() => setSending(false));
    },
    [accessToken, activeConversationId, refreshConversations],
  );

  const retry = useCallback(() => {
    if (lastFailedMessage) sendMessage(lastFailedMessage);
  }, [lastFailedMessage, sendMessage]);

  const removeConversation = useCallback(
    (id: string) => {
      if (!accessToken) return;
      deleteConversation(accessToken, id)
        .then(() => {
          refreshConversations();
          if (activeConversationId === id) startNewConversation();
        })
        .catch(() => {
          setError("Failed to delete that conversation.");
        });
    },
    [accessToken, activeConversationId, refreshConversations, startNewConversation],
  );

  return {
    conversations,
    activeConversationId,
    messages,
    loadingConversations,
    loadingMessages,
    sending,
    error,
    loadConversation,
    startNewConversation,
    sendMessage,
    retry,
    removeConversation,
  };
}
