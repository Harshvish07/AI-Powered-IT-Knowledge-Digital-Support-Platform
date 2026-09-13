import { apiRequest } from "@/lib/apiClient";
import type { KnowledgeDocumentDetail, KnowledgeDocumentPublic } from "@/types/api";

export interface ListDocumentsParams {
  category?: string;
  search?: string;
}

function buildQuery(params: ListDocumentsParams): string {
  const query = new URLSearchParams();
  if (params.category) query.set("category", params.category);
  if (params.search) query.set("search", params.search);
  const queryString = query.toString();
  return queryString ? `?${queryString}` : "";
}

export function listDocuments(
  accessToken: string,
  params: ListDocumentsParams = {},
): Promise<KnowledgeDocumentPublic[]> {
  return apiRequest<KnowledgeDocumentPublic[]>(`/api/knowledge${buildQuery(params)}`, {
    accessToken,
  });
}

export function getDocument(accessToken: string, id: string): Promise<KnowledgeDocumentDetail> {
  return apiRequest<KnowledgeDocumentDetail>(`/api/knowledge/${id}`, { accessToken });
}

export interface UploadDocumentInput {
  file: File;
  title: string;
  category: string;
  description?: string;
}

export function uploadDocument(
  accessToken: string,
  input: UploadDocumentInput,
): Promise<KnowledgeDocumentDetail> {
  const formData = new FormData();
  formData.set("file", input.file);
  formData.set("title", input.title);
  formData.set("category", input.category);
  if (input.description) formData.set("description", input.description);

  return apiRequest<KnowledgeDocumentDetail>("/api/admin/knowledge/upload", {
    method: "POST",
    accessToken,
    body: formData,
  });
}

export function deleteDocument(accessToken: string, id: string): Promise<void> {
  return apiRequest<void>(`/api/admin/knowledge/${id}`, {
    method: "DELETE",
    accessToken,
  });
}

export function reindexDocument(accessToken: string, id: string): Promise<KnowledgeDocumentDetail> {
  return apiRequest<KnowledgeDocumentDetail>(`/api/admin/knowledge/${id}/reindex`, {
    method: "POST",
    accessToken,
  });
}
