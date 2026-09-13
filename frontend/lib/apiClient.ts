import { API_BASE_URL } from "@/lib/config";
import type { ApiErrorBody } from "@/types/api";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

interface ApiRequestOptions extends RequestInit {
  accessToken?: string | null;
}

/** Fetch wrapper for the backend API: always sends the refresh cookie, attaches
 * the Bearer token when provided, and turns non-2xx responses into ApiError. */
export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { accessToken, headers, ...rest } = options;
  // A FormData body (file uploads) must NOT get an explicit Content-Type —
  // the browser needs to set its own multipart boundary.
  const isFormData = rest.body instanceof FormData;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    credentials: "include",
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...headers,
    },
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const body = (await response.json()) as ApiErrorBody;
      if (body.detail) message = body.detail;
    } catch {
      // No JSON body to read a message from.
    }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
