// Placeholder TS types — Phase 2 agents will expand per domain.

export interface User {
  id: string;
  email: string;
  client_id: string;
  created_at: string;
}

export interface Client {
  id: string;
  name: string;
  api_key?: string;
  created_at: string;
}

export interface Flag {
  id: string;
  key: string;
  name: string;
  description?: string;
  enabled: boolean;
  client_id: string;
  created_at: string;
  updated_at: string;
}

export interface AuditEntry {
  id: string;
  actor_id: string;
  action: string;
  target_type: string;
  target_id: string;
  diff?: Record<string, unknown>;
  created_at: string;
}

export interface EvalResult {
  flag_key: string;
  value: unknown;
  variant?: string;
  reason: string;
}

export interface ApiError {
  detail: string;
  code?: string;
}
