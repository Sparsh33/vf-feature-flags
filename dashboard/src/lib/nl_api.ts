import { api } from "@/lib/api";
import type { NLChatRequest, NLChatResponse } from "@/types/feature_api";

export const nlApi = {
  chat: async (payload: NLChatRequest): Promise<NLChatResponse> => {
    const { data } = await api.post<NLChatResponse>("/nl/chat", payload);
    return data;
  },
};
