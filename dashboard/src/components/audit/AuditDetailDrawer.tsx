import { X } from "lucide-react";
import { format, parseISO } from "date-fns";

import type { AuditLog } from "@/types/feature_api";

interface AuditDetailDrawerProps {
  log: AuditLog | null;
  onClose: () => void;
}

function prettyJson(value: Record<string, unknown> | null | undefined): string {
  if (!value) return "(none)";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function formatTs(iso: string): string {
  try {
    return format(parseISO(iso), "yyyy-MM-dd HH:mm:ss 'UTC'");
  } catch {
    return iso;
  }
}

// Diff-highlight: mark keys that changed between before/after with a subtle background.
function diffKeys(
  before: Record<string, unknown> | null | undefined,
  after: Record<string, unknown> | null | undefined,
): Set<string> {
  const keys = new Set<string>();
  const beforeObj = before ?? {};
  const afterObj = after ?? {};
  const allKeys = new Set([
    ...Object.keys(beforeObj),
    ...Object.keys(afterObj),
  ]);
  for (const key of allKeys) {
    const beforeValue = JSON.stringify(beforeObj[key]);
    const afterValue = JSON.stringify(afterObj[key]);
    if (beforeValue !== afterValue) keys.add(key);
  }
  return keys;
}

function renderWithDiff(
  value: Record<string, unknown> | null | undefined,
  changedKeys: Set<string>,
): JSX.Element {
  if (!value) {
    return <span className="text-muted-foreground">(none)</span>;
  }
  return (
    <pre className="whitespace-pre-wrap break-words font-mono text-xs">
      {"{"}
      {"\n"}
      {Object.entries(value).map(([key, val], idx, arr) => (
        <span
          key={key}
          className={
            changedKeys.has(key)
              ? "bg-amber-100 dark:bg-amber-900/40"
              : undefined
          }
        >
          {"  "}
          <span className="text-blue-700 dark:text-blue-300">
            &quot;{key}&quot;
          </span>
          : {JSON.stringify(val)}
          {idx < arr.length - 1 ? "," : ""}
          {"\n"}
        </span>
      ))}
      {"}"}
    </pre>
  );
}

export function AuditDetailDrawer({
  log,
  onClose,
}: AuditDetailDrawerProps): JSX.Element | null {
  if (!log) return null;
  const changedKeys = diffKeys(log.before, log.after);
  return (
    <div className="fixed inset-0 z-50 flex" role="dialog" aria-modal="true">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative ml-auto flex h-full w-full max-w-3xl flex-col overflow-y-auto border-l bg-background shadow-xl">
        <div className="flex items-start justify-between border-b px-5 py-4">
          <div>
            <div className="text-xs uppercase tracking-wide text-muted-foreground">
              Audit entry
            </div>
            <div className="mt-1 font-mono text-sm">{log.action}</div>
            <div className="mt-1 text-xs text-muted-foreground">
              {formatTs(log.ts)}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 hover:bg-muted"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="grid grid-cols-1 gap-4 px-5 py-4 text-xs md:grid-cols-2">
          <div>
            <div className="text-muted-foreground">Actor</div>
            <div className="font-mono">{log.actor_user_id ?? "—"}</div>
          </div>
          <div>
            <div className="text-muted-foreground">Resource</div>
            <div className="font-mono">
              {log.resource_type}:{log.resource_id}
            </div>
          </div>
          <div>
            <div className="text-muted-foreground">Entry id</div>
            <div className="font-mono">{log.id}</div>
          </div>
        </div>
        <div className="grid flex-1 grid-cols-1 gap-4 border-t px-5 py-4 md:grid-cols-2">
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase text-muted-foreground">
              Before
            </h3>
            <div className="rounded-md border bg-muted/30 p-3">
              {log.before ? (
                renderWithDiff(log.before, changedKeys)
              ) : (
                <pre className="font-mono text-xs text-muted-foreground">
                  {prettyJson(log.before)}
                </pre>
              )}
            </div>
          </div>
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase text-muted-foreground">
              After
            </h3>
            <div className="rounded-md border bg-muted/30 p-3">
              {log.after ? (
                renderWithDiff(log.after, changedKeys)
              ) : (
                <pre className="font-mono text-xs text-muted-foreground">
                  {prettyJson(log.after)}
                </pre>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
