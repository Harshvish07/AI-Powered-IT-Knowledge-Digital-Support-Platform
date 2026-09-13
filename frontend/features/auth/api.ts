import { apiRequest } from "@/lib/apiClient";
import type { TokenResponse, UserPublic } from "@/types/api";

export function registerRequest(
  email: string,
  password: string,
  fullName: string,
): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
}

export function loginRequest(email: string, password: string): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function refreshRequest(): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/api/auth/refresh", { method: "POST" });
}

export function logoutRequest(accessToken: string | null): Promise<{ message: string }> {
  return apiRequest<{ message: string }>("/api/auth/logout", {
    method: "POST",
    accessToken,
  });
}

export function getMe(accessToken: string): Promise<UserPublic> {
  return apiRequest<UserPublic>("/api/users/me", { accessToken });
}

export function listUsers(accessToken: string): Promise<UserPublic[]> {
  return apiRequest<UserPublic[]>("/api/users", { accessToken });
}
