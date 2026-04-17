import { useMemo, useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { FileText } from "lucide-react";

import { auditApi } from "@/lib/audit_api";
import type { AuditLog, AuditLogListResponse } from "@/types/feature_api";
import {
  AuditFilters,
  type AuditFilterState,
} from "@/components/audit/AuditFilters";
import { AuditLogTable } from "@/components/audit/AuditLogTable";
import { AuditDetailDrawer } from "@/components/audit/AuditDetailDrawer";

const PAGE_SIZE = 50;

const INITIAL_FILTERS: AuditFilterState = {
  actions: [],
  resourceType: "",
  resourceId: "",
  fromTs: "",
  toTs: "",
};

function toIsoFromLocal(value: string): string | undefined {
  if (!value) return undefined;
  return new Date(value).toISOString();
}

export default function AuditLogPage(): JSX.Element {
  const [filters, setFilters] = useState<AuditFilterState>(INITIAL_FILTERS);
  const [selected, setSelected] = useState<AuditLog | null>(null);

  // Backend accepts one `action` only — if multiple are selected, send the first
  // and TODO: request a backend change to accept an array. For MVP, client-side
  // filter the additional actions from the response.
  const primaryAction = filters.actions[0];

  const queryParams = useMemo(
    () => ({
      action: primaryAction,
      resource_type: filters.resourceType || undefined,
      resource_id: filters.resourceId || undefined,
      from_ts: toIsoFromLocal(filters.fromTs),
      to_ts: toIsoFromLocal(filters.toTs),
    }),
    [primaryAction, filters.resourceType, filters.resourceId, filters.fromTs, filters.toTs]
  );

  const infinite = useInfiniteQuery<AuditLogListResponse>({
    queryKey: ["audit-logs", queryParams],
    queryFn: async ({ pageParam }) => {
      const skip = typeof pageParam === "number" ? pageParam : 0;
      return auditApi.list({ ...queryParams, limit: PAGE_SIZE, skip });
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) => {
      const loaded = pages.reduce((acc, page) => acc + page.logs.length, 0);
      if (loaded >= lastPage.total) return undefined;
      return loaded;
    },
  });

  const allLogs = useMemo(() => {
    const flat = infinite.data?.pages.flatMap((page) => page.logs) ?? [];
    // Client-side narrow when multiple actions are selected.
    if (filters.actions.length <= 1) return flat;
    const set = new Set(filters.actions);
    return flat.filter((log) => set.has(log.action));
  }, [infinite.data, filters.actions]);

  const total = infinite.data?.pages[0]?.total ?? 0;

  return (
    <div className="flex flex-col gap-4 p-6">
      <div className="flex items-center gap-2">
        <FileText className="h-5 w-5 text-muted-foreground" />
        <h1 className="text-xl font-semibold">Audit log</h1>
        {total > 0 ? (
          <span className="text-xs text-muted-foreground">· {total} entries</span>
        ) : null}
      </div>
      <AuditFilters value={filters} onChange={setFilters} />
      {infinite.isLoading ? (
        <div className="py-10 text-center text-sm text-muted-foreground">
          Loading audit logs…
        </div>
      ) : infinite.isError ? (
        <div className="py-10 text-center text-sm text-destructive">
          Failed to load audit logs.
        </div>
      ) : (
        <>
          <AuditLogTable
            logs={allLogs}
            onRowClick={(log) => setSelected(log)}
          />
          {infinite.hasNextPage ? (
            <div className="flex justify-center">
              <button
                type="button"
                onClick={() => infinite.fetchNextPage()}
                disabled={infinite.isFetchingNextPage}
                className="rounded-md border bg-background px-4 py-2 text-sm hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
              >
                {infinite.isFetchingNextPage ? "Loading…" : "Load more"}
              </button>
            </div>
          ) : null}
        </>
      )}
      <AuditDetailDrawer log={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
