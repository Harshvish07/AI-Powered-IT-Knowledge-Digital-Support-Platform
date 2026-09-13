import { apiRequest } from "@/lib/apiClient";
import type {
  TicketCategory,
  TicketCommentPublic,
  TicketDetail,
  TicketPriority,
  TicketPublic,
  TicketStatus,
} from "@/types/api";

export function listMyTickets(accessToken: string): Promise<TicketPublic[]> {
  return apiRequest<TicketPublic[]>("/api/tickets", { accessToken });
}

export function listAllTickets(accessToken: string): Promise<TicketPublic[]> {
  return apiRequest<TicketPublic[]>("/api/admin/tickets", { accessToken });
}

export function getTicket(accessToken: string, id: string): Promise<TicketDetail> {
  return apiRequest<TicketDetail>(`/api/tickets/${id}`, { accessToken });
}

export interface CreateTicketInput {
  title: string;
  description: string;
  category: TicketCategory;
  priority: TicketPriority;
}

export function createTicket(accessToken: string, input: CreateTicketInput): Promise<TicketDetail> {
  return apiRequest<TicketDetail>("/api/tickets", {
    method: "POST",
    accessToken,
    body: JSON.stringify(input),
  });
}

export function addComment(
  accessToken: string,
  ticketId: string,
  content: string,
): Promise<TicketCommentPublic> {
  return apiRequest<TicketCommentPublic>(`/api/tickets/${ticketId}/comments`, {
    method: "POST",
    accessToken,
    body: JSON.stringify({ content }),
  });
}

export interface UpdateTicketInput {
  status?: TicketStatus;
  priority?: TicketPriority;
}

export function updateTicket(
  accessToken: string,
  ticketId: string,
  input: UpdateTicketInput,
): Promise<TicketDetail> {
  return apiRequest<TicketDetail>(`/api/admin/tickets/${ticketId}`, {
    method: "PATCH",
    accessToken,
    body: JSON.stringify(input),
  });
}

export function assignTicket(
  accessToken: string,
  ticketId: string,
  assignedTo: string | null,
): Promise<TicketDetail> {
  return apiRequest<TicketDetail>(`/api/admin/tickets/${ticketId}/assign`, {
    method: "POST",
    accessToken,
    body: JSON.stringify({ assigned_to: assignedTo }),
  });
}
