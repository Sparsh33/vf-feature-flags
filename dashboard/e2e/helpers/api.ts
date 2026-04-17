import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));

/**
 * Thin fetch-based wrapper around the backend API.
 * Dashboard vite dev server proxies /api/* to http://localhost:8000
 * but helpers hit the backend directly since they are not browser code.
 */

export const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

interface RequestOptions {
  token?: string;
  apiKey?: string;
  body?: unknown;
  params?: Record<string, string | number | undefined>;
}

function buildUrl(urlPath: string, params?: RequestOptions["params"]): string {
  const url = new URL(urlPath, BACKEND_URL);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function request<T>(
  method: string,
  urlPath: string,
  options: RequestOptions = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (options.token) headers["Authorization"] = `Bearer ${options.token}`;
  if (options.apiKey) headers["X-Client-API-Key"] = options.apiKey;

  const response = await fetch(buildUrl(urlPath, options.params), {
    method,
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${method} ${urlPath} failed: ${response.status} ${text}`);
  }
  // 204 / empty body tolerant.
  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export const backendApi = {
  evaluate: (
    flagKey: string,
    payload: { user_id: string | number; attributes?: Record<string, unknown> },
    apiKey: string
  ) => request(`POST`, `/v1/evaluate/${flagKey}`, { apiKey, body: payload }),
  listFlags: (token: string) => request<{ flags: Array<{ id: string; flag_key: string }> }>(
    `GET`,
    `/api/flags/`,
    { token }
  ),
  getHealth: () => request<{ status: string }>(`GET`, `/health`),
};

/**
 * Seed N evaluation calls against a given flag to produce analytics data.
 */
export async function seedEvaluations(
  flagKey: string,
  apiKey: string,
  count = 20
): Promise<void> {
  for (let index = 0; index < count; index += 1) {
    try {
      await backendApi.evaluate(flagKey, { user_id: `user_${index}` }, apiKey);
    } catch (error) {
      // Swallow individual errors so one bad call doesn't abort the whole seed.
      // eslint-disable-next-line no-console
      console.warn(`seedEvaluations[${index}]`, (error as Error).message);
    }
  }
}

export const STATE_DIR = path.resolve(HERE, "..", ".state");
export const FLAG_INFO_FILE = path.join(STATE_DIR, "flag-info.json");

export interface SeededFlagInfo {
  id: string;
  flag_key: string;
}

export function writeFlagInfo(info: SeededFlagInfo): void {
  if (!fs.existsSync(STATE_DIR)) fs.mkdirSync(STATE_DIR, { recursive: true });
  fs.writeFileSync(FLAG_INFO_FILE, JSON.stringify(info, null, 2), "utf-8");
}

export function readFlagInfo(): SeededFlagInfo | null {
  if (!fs.existsSync(FLAG_INFO_FILE)) return null;
  return JSON.parse(fs.readFileSync(FLAG_INFO_FILE, "utf-8")) as SeededFlagInfo;
}
