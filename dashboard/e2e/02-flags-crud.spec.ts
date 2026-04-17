import { expect, test } from "@playwright/test";

import { writeFlagInfo } from "./helpers/api";
import {
  AUTH_STATE_FILE,
  captureApiKeyAndConfirm,
  installApiProxy,
  signupUi,
  uniqueEmail,
} from "./helpers/auth";

test.describe.configure({ mode: "serial" });

// Use the auth state captured by 01-auth.spec.ts so we stay signed in.
test.use({ storageState: AUTH_STATE_FILE });

test.beforeEach(async ({ page }) => {
  await installApiProxy(page);
});

const FLAG_KEY = `rollout_playwright_${Date.now()}`;

test.describe("Flags CRUD", () => {
  test("create flag via UI with two cohorts summing to 100", async ({
    page,
  }) => {
    await page.goto("/flags");
    await page.getByRole("button", { name: /new flag/i }).click();

    await expect(page).toHaveURL(/\/flags\/new$/);

    await page.getByLabel("Flag key").fill(FLAG_KEY);
    await page.getByLabel("Name").fill("Playwright rollout");
    await page.getByLabel("Default value (JSON)").fill('{"mode":"off"}');

    // Add two cohorts: A 60% and B 40%.
    const addCohort = page.getByRole("button", { name: /add cohort/i });
    await addCohort.click();
    await addCohort.click();

    const nameInputs = page.locator('input[id^="cohort-name-"]');
    const pctInputs = page.locator('input[id^="cohort-pct-"]');
    const valInputs = page.locator('textarea[id^="cohort-val-"]');

    await nameInputs.nth(0).fill("A");
    await pctInputs.nth(0).fill("60");
    await valInputs.nth(0).fill('{"mode":"on","variant":"v1"}');

    await nameInputs.nth(1).fill("B");
    await pctInputs.nth(1).fill("40");
    await valInputs.nth(1).fill('{"mode":"on","variant":"v2"}');

    // Success badge should say "100%".
    const sumBadge = page.getByText(/^100%$/);
    await expect(sumBadge).toBeVisible();

    await page.getByRole("button", { name: /create flag/i }).click();

    // Wait for the mutation to succeed and navigate us off /flags/new to the
    // new detail page at /flags/<id>.
    await expect(page).toHaveURL(/\/flags\/(?!new$)[^/]+$/, { timeout: 10_000 });

    // Pick up flag id from the URL and stash for downstream specs.
    const match = page.url().match(/\/flags\/([^/?#]+)/);
    const flagId = match?.[1];
    expect(flagId, "flag id must be in URL").toBeTruthy();
    writeFlagInfo({ id: flagId!, flag_key: FLAG_KEY });

    // Navigate back and confirm it's in the list.
    await page.goto("/flags");
    await expect(page.getByText(FLAG_KEY)).toBeVisible();
  });

  test("cohort sum over 100 disables save and shows red badge", async ({
    page,
  }) => {
    await page.goto("/flags");
    // Flag key text is not clickable; navigate via the row's Edit button.
    const row = page.locator("tr", { hasText: FLAG_KEY });
    await row.getByRole("button", { name: "Edit" }).click();

    await expect(page).toHaveURL(/\/flags\/[^/]+$/);

    const pctInputs = page.locator('input[id^="cohort-pct-"]');
    await pctInputs.nth(0).fill("70");

    await expect(page.getByText(/^110%$/)).toBeVisible();
    await expect(
      page.getByRole("button", { name: /save changes/i }),
    ).toBeDisabled();
  });

  test("distribute remaining brings sum back to 100", async ({ page }) => {
    await page.goto("/flags");
    const row = page.locator("tr", { hasText: FLAG_KEY });
    await row.getByRole("button", { name: "Edit" }).click();

    const pctInputs = page.locator('input[id^="cohort-pct-"]');
    // Force imbalance first so the distribute button has work to do.
    await pctInputs.nth(0).fill("70");
    await expect(page.getByText(/^110%$/)).toBeVisible();

    await page.getByRole("button", { name: /distribute remaining/i }).click();

    await expect(page.getByText(/^100%$/)).toBeVisible();
  });

  test("soft delete from list hides the row", async ({ page }) => {
    // Create a throwaway flag specifically for deletion.
    const throwawayKey = `pw_del_${Date.now()}`;
    await page.goto("/flags/new");
    await page.getByLabel("Flag key").fill(throwawayKey);
    await page.getByLabel("Name").fill("Throwaway");
    await page.getByLabel("Default value (JSON)").fill('"off"');
    // Backend requires cohorts summing to 100 — add a single 100% cohort.
    await page.getByRole("button", { name: /add cohort/i }).click();
    await page.locator('input[id^="cohort-name-"]').nth(0).fill("only");
    await page.locator('input[id^="cohort-pct-"]').nth(0).fill("100");
    await page.locator('textarea[id^="cohort-val-"]').nth(0).fill('"on"');
    await page.getByRole("button", { name: /create flag/i }).click();
    // Wait for navigation to the detail page — URL must not be /flags/new.
    await expect(page).toHaveURL(/\/flags\/(?!new$)[^/]+$/, {
      timeout: 10_000,
    });

    await page.goto("/flags");
    await expect(page.getByText(throwawayKey)).toBeVisible();

    const row = page.locator("tr", { hasText: throwawayKey });
    await row.getByRole("button", { name: "Delete" }).click();

    // Confirm in AlertDialog.
    const dialog = page.getByRole("alertdialog");
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: /^delete$/i }).click();

    // Either the row disappears or a toast appears.
    await expect(page.getByText(/flag deleted/i).first()).toBeVisible({
      timeout: 5_000,
    });
    await expect(page.getByText(throwawayKey)).toHaveCount(0);
  });

  test("cross-client isolation: second signup cannot see first client's flag", async ({
    browser,
  }) => {
    // Brand new clean browser context — no storageState.
    const otherContext = await browser.newContext();
    const otherPage = await otherContext.newPage();

    const secondEmail = uniqueEmail("pw-second");
    await signupUi(otherPage, secondEmail, "Password123!", "Second Co");
    await captureApiKeyAndConfirm(otherPage);

    await otherPage.goto("/flags");
    // The flag created by the first user must not appear.
    await expect(otherPage.getByText(FLAG_KEY)).toHaveCount(0);

    await otherContext.close();
  });
});
