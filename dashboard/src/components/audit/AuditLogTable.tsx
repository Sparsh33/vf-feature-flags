import { format, parseISO } from "date-fns";

import type { AuditLog } from "@/types/feature_api";
import { cn } from "@/lib/utils";

interface AuditLogTableProps {
  logs: AuditLog[];
  onRowClick: (log: AuditLog) => void;
}

function actionBadgeClass(action: string): string {
  if (action.endsWith(".create") || action === "user.signup") {
    return "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200";
  }
  if (action.endsWith(".update")) {
    return "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200";
  }
  if (action.endsWith(".delete")) {
    return "bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-200";
  }
  if (action === "client.rotate_api_key") {
    return "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200";
  }
  if (action === "user.login") {
    return "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100";
  }
  return "bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200";
}

function formatTs(iso: string): string {
  try {
    return format(parseISO(iso), "yyyy-MM-dd HH:mm:ss");
  } catch {
    return iso;
  }
}

export function AuditLogTable({
  logs,
  onRowClick,
}: AuditLogTableProps): JSX.Element {
  if (logs.length === 0) {
    return (
      <div className="rounded-md border border-dashed p-10 text-center text-sm text-muted-foreground">
        No audit logs match your filters.
      </div>
    );
  }
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-left text-xs uppercase text-muted-foreground">
          <tr>
            <th className="px-3 py-2 font-medium">Timestamp</th>
            <th className="px-3 py-2 font-medium">Actor</th>
            <th className="px-3 py-2 font-medium">Action</th>
            <th className="px-3 py-2 font-medium">Resource</th>
            <th className="px-3 py-2 font-medium" />
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr
              key={log.id}
              onClick={() => onRowClick(log)}
              className="cursor-pointer border-t hover:bg-muted/40"
            >
              <td className="px-3 py-2 font-mono text-xs tabular-nums">
                {formatTs(log.ts)}
              </td>
              <td className="px-3 py-2 font-mono text-xs">
                {/* TODO: resolve actor_user_id → email via /api/auth/users/:id when endpoint exists. */}
                {log.actor_user_id ?? "—"}
              </td>
              <td className="px-3 py-2">
                <span
                  className={cn(
                    "inline-block rounded px-2 py-0.5 font-mono text-[11px] font-medium",
                    actionBadgeClass(log.action),
                  )}
                >
                  {log.action}
                </span>
              </td>
              <td className="px-3 py-2 font-mono text-xs">
                <span className="text-muted-foreground">
                  {log.resource_type}:
                </span>{" "}
                {log.resource_id}
              </td>
              <td className="px-3 py-2 text-right">
                <span className="text-xs font-medium text-primary underline">
                  View details
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
