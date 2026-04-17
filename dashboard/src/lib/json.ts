// JSON parse/format helpers used by flag editor forms.

export interface JsonParseResult {
  ok: boolean;
  value?: unknown;
  error?: string;
}

export function tryParseJson(text: string): JsonParseResult {
  const trimmed = text.trim();
  if (trimmed === "") return { ok: true, value: null };
  try {
    return { ok: true, value: JSON.parse(trimmed) };
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Invalid JSON";
    return { ok: false, error: msg };
  }
}

export function formatJson(value: unknown): string {
  if (value === undefined || value === null) return "null";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
