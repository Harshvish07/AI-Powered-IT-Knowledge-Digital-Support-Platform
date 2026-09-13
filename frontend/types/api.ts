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
  created_at: string;
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

export type Confidence = "high" | "medium" | "low" | "none";
export type MessageRole = "USER" | "ASSISTANT";

export interface SourceCitation {
  document_id: string;
  document_title: string;
  chunk_id: string;
  page: number | null;
  relevance_score: number;
}

export interface ChatResponse {
  answer: string;
  sources: SourceCitation[];
  conversation_id: string;
  confidence: Confidence;
}

export interface MessageOut {
  id: string;
  role: MessageRole;
  content: string;
  sources: SourceCitation[] | null;
  confidence: string | null;
  created_at: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: MessageOut[];
}

export type TicketCategory =
  "HARDWARE" | "SOFTWARE" | "NETWORK" | "ACCOUNT_ACCESS" | "SECURITY" | "OTHER";
export type TicketPriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type TicketStatus = "OPEN" | "IN_PROGRESS" | "RESOLVED" | "CLOSED";

export interface TicketCommentPublic {
  id: string;
  ticket_id: string;
  user_id: string | null;
  author_name: string | null;
  content: string;
  created_at: string;
}

export interface TicketPublic {
  id: string;
  title: string;
  description: string;
  category: TicketCategory;
  priority: TicketPriority;
  status: TicketStatus;
  created_by: string;
  created_by_name: string | null;
  assigned_to: string | null;
  assigned_to_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface TicketDetail extends TicketPublic {
  comments: TicketCommentPublic[];
}

export interface DailyCount {
  date: string;
  count: number;
}

export interface DashboardMetrics {
  total_users: number;
  active_users: number;
  total_documents: number;
  ready_documents: number;
  failed_documents: number;
  total_tickets: number;
  open_tickets: number;
  in_progress_tickets: number;
  resolved_tickets: number;
  ai_questions: number;
  tickets_by_status: Record<TicketStatus, number>;
  tickets_by_category: Record<TicketCategory, number>;
  documents_by_status: Record<DocumentStatus, number>;
  ai_questions_by_day: DailyCount[];
}

export interface AdminConversationSummary {
  id: string;
  user_id: string;
  user_name: string | null;
  user_email: string | null;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}
