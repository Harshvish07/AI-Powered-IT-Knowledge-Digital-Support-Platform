import { apiRequest } from "@/lib/apiClient";
import type { AdminConversationSummary, DashboardMetrics, UserPublic } from "@/types/api";

export function getDashboardMetrics(accessToken: string): Promise<DashboardMetrics> {
  return apiRequest<DashboardMetrics>("/api/admin/dashboard", { accessToken });
}

export function setUserActive(
  accessToken: string,
  userId: string,
  isActive: boolean,
): Promise<UserPublic> {
  return apiRequest<UserPublic>(`/api/users/${userId}`, {
    method: "PATCH",
    accessToken,
    body: JSON.stringify({ is_active: isActive }),
  });
}

export function listAdminConversations(accessToken: string): Promise<AdminConversationSummary[]> {
  return apiRequest<AdminConversationSummary[]>("/api/admin/conversations", { accessToken });
}
