import type { ExtractedParams } from "@/types/feature_api";
import { cn } from "@/lib/utils";

interface ExtractedParamsPanelProps {
  extracted: ExtractedParams;
}

const FIELDS: { key: keyof ExtractedParams; label: string }[] = [
  { key: "flag_key", label: "flag_key" },
  { key: "name", label: "name" },
  { key: "description", label: "description" },
  { key: "default_value", label: "default_value" },
  { key: "cohorts", label: "cohorts" },
  { key: "parameters_schema", label: "parameters_schema" },
];

function isFilled(value: unknown): boolean {
  if (value === null || value === undefined) return false;
  if (Array.isArray(value) && value.length === 0) return false;
  if (typeof value === "string" && value.length === 0) return false;
  if (typeof value === "object" && !Array.isArray(value) && value !== null) {
    return Object.keys(value as Record<string, unknown>).length > 0;
  }
  return true;
}

function renderValue(value: unknown): string {
  if (value === null || value === undefined) return "pending";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function ExtractedParamsPanel({
  extracted,
}: ExtractedParamsPanelProps): JSX.Element {
  return (
    <div className="flex flex-col gap-3 font-mono text-xs">
      {FIELDS.map((field) => {
        const value = extracted[field.key];
        const filled = isFilled(value);
        return (
          <div
            key={field.key}
            className={cn(
              "rounded-md border p-3",
              filled
                ? "border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/30"
                : "border-dashed border-zinc-300 bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900/30"
            )}
          >
            <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">
              {field.label}
            </div>
            <pre
              className={cn(
                "whitespace-pre-wrap break-words",
                filled ? "text-zinc-900 dark:text-zinc-100" : "italic text-zinc-400"
              )}
            >
              {renderValue(value)}
            </pre>
          </div>
        );
      })}
    </div>
  );
}
