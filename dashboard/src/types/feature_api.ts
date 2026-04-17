// Local types for chat, analytics, and audit pages.
// TODO: fold into `@/types/api.ts` once Agent G has populated the canonical types.

export interface CohortConfig {
  cohort_id?: string;
  name: string;
  percentage: number;
  value: unknown;
  rules?: Record<string, unknown>;
}

export interface FlagCreateRequest {
  flag_key: string;
  name: string;
  description?: string;
  default_value: unknown;
  cohorts?: CohortConfig[];
  parameters_schema?: Record<string, unknown>;
}

export interface ExtractedParams {
  flag_key?: string | null;
  name?: string | null;
  description?: string | null;
  default_value?: unknown;
  cohorts?: CohortConfig[] | null;
  parameters_schema?: Record<string, unknown> | null;
}

export interface NLChatRequest {
  session_id?: string | null;
  message: string;
}

export interface NLChatResponse {
  session_id: string;
  reply: string;
  extracted: ExtractedParams;
  draft_flag?: FlagCreateRequest | null;
  ready_to_commit: boolean;
  committed_flag_id?: string | null;
  compacted: boolean;
}

export interface CohortStats {
  cohort_id?: string | null;
  cohort_name?: string | null;
  count: number;
  percentage: number;
}

export interface FlagAnalyticsResponse {
  flag_id: string;
  flag_key: string;
  total_requests: number;
  per_cohort: CohortStats[];
  time_range: Record<string, string>;
}

export interface TimeSeriesBucket {
  ts: string;
  counts_by_cohort: Record<string, number>;
}

export interface FlagAnalyticsTimeSeriesResponse {
  flag_id: string;
  flag_key: string;
  interval: string;
  buckets: TimeSeriesBucket[];
}

export interface FlagSummary {
  id: string;
  flag_key: string;
  name: string;
  description?: string;
  status?: string;
}

export interface AnalyticsOverviewResponse {
  total_flags: number;
  total_evals_24h: number;
  evals_per_cohort: CohortStats[];
  per_flag: {
    flag_id: string;
    flag_key: string;
    total_requests: number;
    sparkline: TimeSeriesBucket[];
  }[];
}

export interface AuditLog {
  id: string;
  actor_user_id?: string | null;
  action: string;
  resource_type: string;
  resource_id: string;
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
  ts: string;
}

export interface AuditLogListResponse {
  logs: AuditLog[];
  total: number;
}
