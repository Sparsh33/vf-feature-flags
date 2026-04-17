import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { flagsApi, type FlagListParams } from "@/lib/api";
import type {
  FlagConfig,
  FlagCreateRequest,
  FlagListResponse,
  FlagUpdateRequest,
} from "@/types/api";

export const FLAGS_KEY = ["flags"] as const;

export function useFlagsList(params: FlagListParams = {}) {
  return useQuery<FlagListResponse>({
    queryKey: [...FLAGS_KEY, "list", params],
    queryFn: () => flagsApi.list(params),
  });
}

export function useFlag(id: string | undefined) {
  return useQuery<FlagConfig>({
    queryKey: [...FLAGS_KEY, "detail", id],
    queryFn: () => flagsApi.get(id as string),
    enabled: Boolean(id),
  });
}

export function useCreateFlag() {
  const queryClient = useQueryClient();
  return useMutation<FlagConfig, unknown, FlagCreateRequest>({
    mutationFn: (payload) => flagsApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: FLAGS_KEY });
    },
  });
}

export function useUpdateFlag(id: string) {
  const queryClient = useQueryClient();
  return useMutation<FlagConfig, unknown, FlagUpdateRequest>({
    mutationFn: (payload) => flagsApi.update(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: FLAGS_KEY });
    },
  });
}

export function useDeleteFlag() {
  const queryClient = useQueryClient();
  return useMutation<void, unknown, string>({
    mutationFn: (id) => flagsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: FLAGS_KEY });
    },
  });
}
