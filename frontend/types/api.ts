export interface HealthResponse {
  status: string;
}

export type UserRole = "EMPLOYEE" | "ADMIN";

export interface UserPublic {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface ApiErrorBody {
  detail?: string;
}

export type DocumentStatus = "UPLOADING" | "PROCESSING" | "INDEXING" | "READY" | "FAILED";

export interface KnowledgeDocumentPublic {
  id: string;
  title: string;
  filename: string;
  description: string | null;
  category: string;
  status: DocumentStatus;
  version: number;
  file_size_bytes: number;
  uploaded_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeDocumentDetail extends KnowledgeDocumentPublic {
  chunk_count: number;
  error_message: string | null;
}
