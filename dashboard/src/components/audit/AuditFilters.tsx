import { X } from "lucide-react";

export const AUDIT_ACTIONS = [
  "flag.create",
  "flag.update",
  "flag.delete",
  "cohort.update",
  "client.rotate_api_key",
  "user.signup",
  "user.login",
] as const;

export type AuditAction = (typeof AUDIT_ACTIONS)[number];

export const RESOURCE_TYPES = [
  "flag",
  "cohort",
  "client",
  "user",
] as const;

export interface AuditFilterState {
  actions: string[];
  resourceType: string;
  resourceId: string;
  fromTs: string;
  toTs: string;
}

interface AuditFiltersProps {
  value: AuditFilterState;
  onChange: (next: AuditFilterState) => void;
}

export function AuditFilters({ value, onChange }: AuditFiltersProps): JSX.Element {
  const toggleAction = (action: string) => {
    const next = value.actions.includes(action)
      ? value.actions.filter((a) => a !== action)
      : [...value.actions, action];
    onChange({ ...value, actions: next });
  };
  const reset = () => {
    onChange({
      actions: [],
      resourceType: "",
      resourceId: "",
      fromTs: "",
      toTs: "",
    });
  };
  return (
    <div className="flex flex-col gap-3 rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Filters</h2>
        <button
          type="button"
          onClick={reset}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <X className="h-3 w-3" /> Reset
        </button>
      </div>
      <div>
        <div className="mb-1 text-xs font-medium text-muted-foreground">Actions</div>
        <div className="flex flex-wrap gap-1.5">
          {AUDIT_ACTIONS.map((action) => {
            const active = value.actions.includes(action);
            return (
              <button
                key={action}
                type="button"
                onClick={() => toggleAction(action)}
                className={`rounded-full border px-2 py-0.5 font-mono text-[11px] transition ${
                  active
                    ? "border-slate-900 bg-slate-900 text-slate-50 dark:border-slate-50 dark:bg-slate-50 dark:text-slate-900"
                    : "border-zinc-300 text-muted-foreground hover:border-zinc-500"
                }`}
              >
                {action}
              </button>
            );
          })}
        </div>
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
        <div>
          <label className="mb-1 block text-xs font-medium text-muted-foreground">
            Resource type
          </label>
          <select
            value={value.resourceType}
            onChange={(e) => onChange({ ...value, resourceType: e.target.value })}
            className="w-full rounded-md border bg-background px-2 py-1.5 text-sm"
          >
            <option value="">Any</option>
            {RESOURCE_TYPES.map((rt) => (
              <option key={rt} value={rt}>
                {rt}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-muted-foreground">
            Resource id
          </label>
          <input
            type="text"
            value={value.resourceId}
            onChange={(e) => onChange({ ...value, resourceId: e.target.value })}
            placeholder="id filter"
            className="w-full rounded-md border bg-background px-2 py-1.5 font-mono text-xs"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-muted-foreground">
            From
          </label>
          <input
            type="datetime-local"
            value={value.fromTs}
            onChange={(e) => onChange({ ...value, fromTs: e.target.value })}
            className="w-full rounded-md border bg-background px-2 py-1.5 text-xs"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-muted-foreground">
            To
          </label>
          <input
            type="datetime-local"
            value={value.toTs}
            onChange={(e) => onChange({ ...value, toTs: e.target.value })}
            className="w-full rounded-md border bg-background px-2 py-1.5 text-xs"
          />
        </div>
      </div>
    </div>
  );
}
