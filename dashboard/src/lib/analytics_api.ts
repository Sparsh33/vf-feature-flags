import { api } from "@/lib/api";
import type {
  AnalyticsOverviewResponse,
  FlagAnalyticsResponse,
  FlagAnalyticsTimeSeriesResponse,
  FlagSummary,
} from "@/types/feature_api";

export interface AnalyticsTimeParams {
  from_ts?: string;
  to_ts?: string;
}

export interface TimeSeriesParams extends AnalyticsTimeParams {
  interval?: "minute" | "hour" | "day";
}

export const analyticsApi = {
  getFlagAnalytics: async (
    flag_id: string,
    params: AnalyticsTimeParams = {}
  ): Promise<FlagAnalyticsResponse> => {
    const { data } = await api.get<FlagAnalyticsResponse>(
      `/analytics/flags/${flag_id}`,
      { params }
    );
    return data;
  },
  getFlagTimeSeries: async (
    flag_id: string,
    params: TimeSeriesParams = {}
  ): Promise<FlagAnalyticsTimeSeriesResponse> => {
    const { data } = await api.get<FlagAnalyticsTimeSeriesResponse>(
      `/analytics/flags/${flag_id}/time-series`,
      { params }
    );
    return data;
  },
  // TODO: Backend endpoint `/analytics/overview` does not exist yet.
  // MVP fallback: list flags + call getFlagAnalytics per flag (done in page).
  listFlags: async (): Promise<FlagSummary[]> => {
    const { data } = await api.get<FlagSummary[] | { flags: FlagSummary[] }>(
      "/flags"
    );
    if (Array.isArray(data)) return data;
    return data.flags ?? [];
  },
  getTenantOverview: async (): Promise<AnalyticsOverviewResponse> => {
    const { data } = await api.get<AnalyticsOverviewResponse>("/analytics/overview");
    return data;
  },
};
