import { expect, test } from "@playwright/test";

import {
  AUTH_STATE_FILE,
  captureApiKeyAndConfirm,
  installApiProxy,
  loginUi,
  saveAuth,
  signupUi,
  uniqueEmail,
  writeApiKey,
  writePrimaryUser,
} from "./helpers/auth";

test.describe.configure({ mode: "serial" });

test.beforeEach(async ({ page }) => {
  await installApiProxy(page);
});

test.describe("Auth flows", () => {
  const password = "Password123!";
  const email = uniqueEmail("pw-primary");
  const clientName = "Playwright Co";

  test("signup happy path captures API key and lands on /flags", async ({
    page,
  }) => {
    await signupUi(page, email, password, clientName);

    // The copy-once modal appears and holds the API key until dismissed.
    const apiKey = await captureApiKeyAndConfirm(page);
    expect(apiKey, "API key should be shown in copy-once modal").not.toBeNull();
    expect(apiKey!.length).toBeGreaterThan(10);

    await expect(page).toHaveURL(/\/flags$/, { timeout: 10_000 });

    // Stash for downstream specs.
    writePrimaryUser({ email, password, clientName });
    writeApiKey(apiKey!);
    await saveAuth(page, AUTH_STATE_FILE);
  });

  test("login happy path after logout", async ({ page }) => {
    // Start by clearing any residual auth: log in fresh using stored user.
    await page.goto("/login");
    await page.evaluate(() => localStorage.clear());

    await loginUi(page, email, password);
    await expect(page).toHaveURL(/\/flags$/);
  });

  test("login with bad credentials shows an error", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill("wrong-password-xyz");
    await page.getByRole("button", { name: /sign in/i }).click();

    // Either a destructive toast or the form stays on /login.
    await expect(page).toHaveURL(/\/login$/, { timeout: 5_000 });
    // Toast shows "Login failed" — match the visible title div, not the aria-live announcer.
    const toast = page.getByText(/login failed/i).first();
    await expect(toast).toBeVisible({ timeout: 5_000 });
  });

  test("me endpoint persists email in header across reload", async ({
    page,
  }) => {
    await loginUi(page, email, password);
    await expect(page.getByText(email)).toBeVisible();
    await page.reload();
    await expect(page.getByText(email)).toBeVisible();
  });
});
