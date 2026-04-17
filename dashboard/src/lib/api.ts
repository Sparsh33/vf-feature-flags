import axios, { AxiosInstance, InternalAxiosRequestConfig } from "axios";

import type {
  AnalyticsResponse,
  AuditLogListResponse,
  FlagAnalyticsResponse,
  FlagAnalyticsTimeSeriesResponse,
  FlagConfig,
  FlagCreateRequest,
  FlagListResponse,
  FlagUpdateRequest,
  LoginRequest,
  LoginResponse,
  NLChatRequest,
  NLChatResponse,
  RotateApiKeyResponse,
  SignupRequest,
  SignupResponse,
  User,
} from "@/types/api";

export const JWT_STORAGE_KEY = "authToken";

export function getStoredToken(): string | null {
  return localStorage.getItem(JWT_STORAGE_KEY);
}

export function setStoredToken(token: string | null): void {
  if (token === null) {
    localStorage.removeItem(JWT_STORAGE_KEY);
  } else {
    localStorage.setItem(JWT_STORAGE_KEY, token);
  }
}

export const api: AxiosInstance = axios.create({
  baseURL: "/api",
  timeout: 30000,
});

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Global 401 handler: clear token and redirect to login.
let redirecting = false;
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      setStoredToken(null);
      if (!redirecting && typeof window !== "undefined") {
        redirecting = true;
        const path = window.location.pathname;
        if (path !== "/login" && path !== "/signup") {
          window.location.assign("/login");
        }
        setTimeout(() => {
          redirecting = false;
        }, 1000);
      }
    }
    return Promise.reject(error);
  },
);

// ---------- Auth ----------

export const authApi = {
  signup: (payload: SignupRequest): Promise<SignupResponse> =>
    api.post<SignupResponse>("/auth/signup", payload).then((r) => r.data),
  login: (payload: LoginRequest): Promise<LoginResponse> =>
    api.post<LoginResponse>("/auth/login", payload).then((r) => r.data),
  me: (): Promise<User> => api.get<User>("/auth/me").then((r) => r.data),
  rotateApiKey: (): Promise<RotateApiKeyResponse> =>
    api
      .post<RotateApiKeyResponse>("/clients/rotate-api-key")
      .then((r) => r.data),
};

// ---------- Flags ----------

export interface FlagListParams {
  status?: string;
  limit?: number;
  skip?: number;
}

export const flagsApi = {
  list: (params: FlagListParams = {}): Promise<FlagListResponse> =>
    api.get<FlagListResponse>("/flags/", { params }).then((r) => r.data),
  get: (id: string): Promise<FlagConfig> =>
    api.get<FlagConfig>(`/flags/${id}`).then((r) => r.data),
  create: (payload: FlagCreateRequest): Promise<FlagConfig> =>
    api.post<FlagConfig>("/flags/", payload).then((r) => r.data),
  update: (id: string, payload: FlagUpdateRequest): Promise<FlagConfig> =>
    api.patch<FlagConfig>(`/flags/${id}`, payload).then((r) => r.data),
  remove: (id: string): Promise<void> =>
    api.delete(`/flags/${id}`).then(() => undefined),
};

// ---------- NL Chat (Agent H will consume) ----------

export const nlApi = {
  chat: (payload: NLChatRequest): Promise<NLChatResponse> =>
    api.post<NLChatResponse>("/nl/chat", payload).then((r) => r.data),
};

// ---------- Analytics (Agent H will consume) ----------

export interface AnalyticsParams {
  start?: string;
  end?: string;
  interval?: string;
}

export const analyticsApi = {
  getOverview: (params: AnalyticsParams = {}): Promise<AnalyticsResponse> =>
    api
      .get<AnalyticsResponse>("/analytics/overview", { params })
      .then((r) => r.data),
  getFlagAnalytics: (
    flagId: string,
    params: AnalyticsParams = {},
  ): Promise<FlagAnalyticsResponse> =>
    api
      .get<FlagAnalyticsResponse>(`/analytics/flags/${flagId}`, { params })
      .then((r) => r.data),
  getFlagTimeSeries: (
    flagId: string,
    params: AnalyticsParams = {},
  ): Promise<FlagAnalyticsTimeSeriesResponse> =>
    api
      .get<FlagAnalyticsTimeSeriesResponse>(
        `/analytics/flags/${flagId}/timeseries`,
        { params },
      )
      .then((r) => r.data),
};

// ---------- Audit (Agent H will consume) ----------

export interface AuditListParams {
  resource_type?: string;
  resource_id?: string;
  action?: string;
  actor_user_id?: string;
  limit?: number;
  skip?: number;
}

export const auditApi = {
  list: (params: AuditListParams = {}): Promise<AuditLogListResponse> =>
    api.get<AuditLogListResponse>("/audit/", { params }).then((r) => r.data),
};
