import type { CohortConfig, FlagCreateRequest } from "@/types/feature_api";
import { cn } from "@/lib/utils";

interface DraftFlagPreviewProps {
  draft: FlagCreateRequest | null;
  readyToCommit: boolean;
  committing: boolean;
  committedFlagId: string | null;
  onCommit: () => void;
}

function totalPct(cohorts: CohortConfig[] | undefined): number {
  if (!cohorts) return 0;
  return cohorts.reduce((acc, cohort) => acc + (cohort.percentage || 0), 0);
}

function renderCohortValue(value: unknown): string {
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function DraftFlagPreview({
  draft,
  readyToCommit,
  committing,
  committedFlagId,
  onCommit,
}: DraftFlagPreviewProps): JSX.Element {
  if (!draft) {
    return (
      <div className="rounded-md border border-dashed border-zinc-300 p-6 text-center text-sm text-muted-foreground">
        Describe the flag you want and the draft will appear here.
      </div>
    );
  }
  const pct = totalPct(draft.cohorts);
  const pctValid = pct === 100 || pct === 0;
  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-md border p-3">
        <div className="flex items-center gap-2">
          <span className="rounded bg-slate-900 px-2 py-0.5 font-mono text-xs text-slate-50">
            {draft.flag_key}
          </span>
          <span className="text-sm font-medium">{draft.name}</span>
        </div>
        {draft.description ? (
          <p className="mt-2 text-xs text-muted-foreground">
            {draft.description}
          </p>
        ) : null}
        <div className="mt-2 flex items-center gap-2 text-xs">
          <span className="text-muted-foreground">default:</span>
          <span className="rounded bg-zinc-100 px-2 py-0.5 font-mono dark:bg-zinc-800">
            {renderCohortValue(draft.default_value)}
          </span>
        </div>
      </div>
      {draft.cohorts && draft.cohorts.length > 0 ? (
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium">
              Cohorts ({draft.cohorts.length})
            </span>
            <span
              className={cn(
                "font-mono",
                pctValid ? "text-emerald-600" : "text-rose-600",
              )}
            >
              total: {pct}%
            </span>
          </div>
          {draft.cohorts.map((cohort, idx) => (
            <div key={idx} className="rounded-md border p-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium">{cohort.name}</span>
                <span className="font-mono">{cohort.percentage}%</span>
              </div>
              <div className="mt-1 h-1.5 w-full overflow-hidden rounded bg-zinc-200 dark:bg-zinc-800">
                <div
                  className="h-full bg-emerald-500"
                  style={{ width: `${Math.min(100, cohort.percentage)}%` }}
                />
              </div>
              <div className="mt-1 flex items-center gap-2 text-[11px]">
                <span className="text-muted-foreground">value:</span>
                <span className="font-mono">
                  {renderCohortValue(cohort.value)}
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : null}
      <button
        type="button"
        onClick={onCommit}
        disabled={!readyToCommit || committing || Boolean(committedFlagId)}
        className={cn(
          "w-full rounded-md px-4 py-2 text-sm font-semibold transition",
          readyToCommit && !committedFlagId
            ? "bg-emerald-600 text-white hover:bg-emerald-700"
            : "cursor-not-allowed bg-zinc-200 text-zinc-500 dark:bg-zinc-800",
        )}
      >
        {committedFlagId
          ? "Flag created"
          : committing
            ? "Creating…"
            : readyToCommit
              ? "Commit flag"
              : "Not ready to commit"}
      </button>
    </div>
  );
}
