import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { Browser, BrowserContext, Page, expect } from "@playwright/test";

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const STATE_DIR = path.resolve(HERE, "..", ".state");
export const AUTH_STATE_FILE = path.join(STATE_DIR, "auth.json");
export const API_KEY_FILE = path.join(STATE_DIR, "api-key.txt");
export const PRIMARY_USER_FILE = path.join(STATE_DIR, "primary-user.json");

/**
 * The dashboard is served from a Docker container whose Vite dev server proxies
 * /api/* to http://localhost:8000 — but from *inside the container* localhost
 * is the container itself, so the proxy fails with ECONNREFUSED. The backend is
 * reachable from the host (where Playwright runs) via BACKEND_URL.
 *
 * To keep the browser-side app unchanged (it calls /api/* via relative URLs) we
 * intercept /api/** requests at the Playwright layer and forward them directly
 * to BACKEND_URL, bypassing the broken container-local proxy.
 */
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function installApiProxy(page: Page): Promise<void> {
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const originalUrl = new URL(request.url());
    const forwardedUrl = `${BACKEND_URL}${originalUrl.pathname}${originalUrl.search}`;
    const headers = { ...request.headers() };
    // Strip host-related headers so fetch recomputes them.
    delete headers.host;
    delete headers["content-length"];
    try {
      const response = await page.request.fetch(forwardedUrl, {
        method: request.method(),
        headers,
        data: request.postDataBuffer() ?? undefined,
      });
      const body = await response.body();
      const responseHeaders = response.headers();
      // Strip hop-by-hop and encoding headers that would confuse the browser.
      delete responseHeaders["content-encoding"];
      delete responseHeaders["transfer-encoding"];
      delete responseHeaders["content-length"];
      await route.fulfill({
        status: response.status(),
        headers: responseHeaders,
        body,
      });
    } catch (error) {
      await route.abort();
      throw error;
    }
  });
}

export interface PrimaryUserInfo {
  email: string;
  password: string;
  clientName: string;
}

export function ensureStateDir(): void {
  if (!fs.existsSync(STATE_DIR)) {
    fs.mkdirSync(STATE_DIR, { recursive: true });
  }
}

export function uniqueEmail(prefix = "test"): string {
  return `${prefix}+${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
}

/**
 * Run through the signup flow in the UI. Stops with the copy-once API key modal open
 * so the caller can capture the key before confirming.
 */
export async function signupUi(
  page: Page,
  email: string,
  password: string,
  clientName: string
): Promise<void> {
  await installApiProxy(page);
  await page.goto("/signup");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByLabel("Client name").fill(clientName);
  await page.getByRole("button", { name: /create account/i }).click();
}

/**
 * Capture the API key shown in the copy-once dialog after signup, then dismiss it.
 * Returns the captured key (or null if not visible).
 */
export async function captureApiKeyAndConfirm(page: Page): Promise<string | null> {
  const dialog = page.getByRole("dialog");
  try {
    await dialog.waitFor({ state: "visible", timeout: 10_000 });
  } catch {
    return null;
  }
  // The key is the only <div> styled as mono inside the dialog.
  const keyBox = dialog.locator("div.font-mono").first();
  await keyBox.waitFor({ state: "visible", timeout: 5_000 });
  const apiKey = (await keyBox.textContent())?.trim() ?? null;
  await dialog.getByRole("button", { name: /saved this/i }).click();
  return apiKey;
}

export async function loginUi(page: Page, email: string, password: string): Promise<void> {
  await installApiProxy(page);
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/flags$/, { timeout: 10_000 });
}

export async function saveAuth(page: Page, file: string = AUTH_STATE_FILE): Promise<void> {
  ensureStateDir();
  await page.context().storageState({ path: file });
}

export async function loadAuthContext(
  browser: Browser,
  file: string = AUTH_STATE_FILE
): Promise<BrowserContext> {
  return browser.newContext({ storageState: file });
}

export function writeApiKey(key: string): void {
  ensureStateDir();
  fs.writeFileSync(API_KEY_FILE, key, "utf-8");
}

export function readApiKey(): string | null {
  if (!fs.existsSync(API_KEY_FILE)) return null;
  return fs.readFileSync(API_KEY_FILE, "utf-8").trim();
}

export function writePrimaryUser(info: PrimaryUserInfo): void {
  ensureStateDir();
  fs.writeFileSync(PRIMARY_USER_FILE, JSON.stringify(info, null, 2), "utf-8");
}

export function readPrimaryUser(): PrimaryUserInfo | null {
  if (!fs.existsSync(PRIMARY_USER_FILE)) return null;
  return JSON.parse(fs.readFileSync(PRIMARY_USER_FILE, "utf-8")) as PrimaryUserInfo;
}
