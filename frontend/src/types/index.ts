/**
 * Shared TypeScript types for the frontend application.
 */

// API response wrapper
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiResponse<T> {
  data: T;
}

// Common entity interfaces
export interface BaseEntity {
  id: string;
  created_at: string;
  updated_at: string | null;
}

// CRM types
export type DealStage =
  | "new_lead"
  | "contacted"
  | "qualified"
  | "proposal"
  | "negotiation"
  | "won"
  | "lost";

export interface Contact extends BaseEntity {
  tenant_id: string;
  email: string | null;
  phone: string | null;
  full_name: string;
  avatar_url: string | null;
  company: string | null;
  tags: string[];
  metadata: Record<string, unknown>;
}

export interface Deal extends BaseEntity {
  tenant_id: string;
  title: string;
  value: number;
  currency: string;
  stage: DealStage;
  contact_id: string;
  assigned_to: string | null;
  expected_close_date: string | null;
  notes: string | null;
}

export interface Pipeline extends BaseEntity {
  name: string;
  stages: PipelineStage[];
}

export interface PipelineStage {
  id: string;
  name: string;
  order: number;
  color: string;
}

// Campaign types
export type CampaignChannel =
  | "whatsapp"
  | "email"
  | "sms"
  | "telegram"
  | "facebook"
  | "instagram";

export type CampaignStatus = "draft" | "scheduled" | "sending" | "completed" | "paused";

export interface Campaign extends BaseEntity {
  name: string;
  channel: CampaignChannel;
  status: CampaignStatus;
  scheduled_at: string | null;
  sent_count: number;
  delivered_count: number;
  read_count: number;
  click_count: number;
  conversion_count: number;
}

// Dashboard metrics
export interface DashboardMetrics {
  total_conversations: number;
  active_conversations: number;
  ai_handled: number;
  human_handled: number;
  avg_response_time_seconds: number;
  satisfaction_score: number;
  total_contacts: number;
  deals_value: number;
}
