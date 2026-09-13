import { apiRequest } from "@/lib/apiClient";
import type { ChatResponse, ConversationDetail, ConversationSummary } from "@/types/api";

export function sendChatMessage(
  accessToken: string,
  message: string,
  conversationId?: string | null,
): Promise<ChatResponse> {
  return apiRequest<ChatResponse>("/api/ai/chat", {
    method: "POST",
    accessToken,
    body: JSON.stringify({ message, conversation_id: conversationId ?? null }),
  });
}

export function listConversations(accessToken: string): Promise<ConversationSummary[]> {
  return apiRequest<ConversationSummary[]>("/api/ai/conversations", { accessToken });
}

export function getConversation(accessToken: string, id: string): Promise<ConversationDetail> {
  return apiRequest<ConversationDetail>(`/api/ai/conversations/${id}`, { accessToken });
}

export function deleteConversation(accessToken: string, id: string): Promise<void> {
  return apiRequest<void>(`/api/ai/conversations/${id}`, {
    method: "DELETE",
    accessToken,
  });
}
