import { api } from "@/lib/api";
import type { AuditLogListResponse } from "@/types/feature_api";

export interface AuditListParams {
  action?: string;
  resource_type?: string;
  resource_id?: string;
  from_ts?: string;
  to_ts?: string;
  limit?: number;
  skip?: number;
}

export const auditApi = {
  list: async (params: AuditListParams = {}): Promise<AuditLogListResponse> => {
    const { data } = await api.get<AuditLogListResponse>("/audit/", { params });
    return data;
  },
};
