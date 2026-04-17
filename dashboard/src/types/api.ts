// Canonical TS interfaces matching backend Pydantic models.
// Shared by Agent G (core dashboard) and Agent H (chat/analytics/audit).

export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

// ---------- Auth / Client ----------

export interface User {
  id: string;
  email: string;
  client_id: string;
  role: string;
}

export interface Client {
  id: string;
  name: string;
}

export interface SignupRequest {
  email: string;
  password: string;
  client_name: string;
}

export interface SignupResponse {
  user: User;
  client: Client;
  api_key: string;
  access_token: string;
  token_type: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  user: User;
  access_token: string;
  token_type: string;
}

export interface RotateApiKeyResponse {
  api_key: string;
}

// ---------- Flags / Cohorts ----------

export interface Cohort {
  id: string;
  name: string;
  percentage: number;
  value: unknown;
}

export interface FlagConfig {
  id: string;
  client_id: string;
  flag_key: string;
  name: string;
  description?: string | null;
  default_value: unknown;
  cohorts: Cohort[];
  parameters_schema?: Record<string, unknown> | null;
  is_deleted: boolean;
  status: string;
  created_at: string;
  updated_at: string;
  created_by?: string | null;
  updated_by?: string | null;
}

export interface FlagCreateRequest {
  flag_key: string;
  name: string;
  description?: string | null;
  default_value?: unknown;
  cohorts?: Cohort[];
  parameters_schema?: Record<string, unknown> | null;
  status?: string;
}

export interface FlagUpdateRequest {
  name?: string;
  description?: string | null;
  default_value?: unknown;
  cohorts?: Cohort[];
  parameters_schema?: Record<string, unknown> | null;
  status?: string;
}

export interface FlagListResponse {
  flags: FlagConfig[];
  total: number;
}

// ---------- Audit ----------

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

// ---------- Analytics ----------

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

export interface AnalyticsResponse {
  total_requests: number;
  total_flags: number;
  per_flag: Array<{
    flag_id: string;
    flag_key: string;
    count: number;
  }>;
  time_range: Record<string, string>;
}

// ---------- NL Chat ----------

export interface ExtractedParams {
  flag_key?: string;
  name?: string;
  description?: string;
  default_value?: unknown;
  cohorts?: Array<{
    name: string;
    percentage: number;
    value: unknown;
  }>;
  parameters_schema?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface NLChatRequest {
  message: string;
  conversation_id?: string;
  extracted_params?: ExtractedParams;
}

export interface NLChatResponse {
  conversation_id: string;
  assistant_message: string;
  extracted_params: ExtractedParams;
  ready_to_create: boolean;
  missing_fields?: string[];
}

// ---------- Errors ----------

export interface ApiError {
  detail: string;
  code?: string;
}
