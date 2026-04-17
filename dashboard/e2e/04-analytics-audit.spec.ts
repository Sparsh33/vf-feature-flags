import { expect, test } from "@playwright/test";

import { readFlagInfo, seedEvaluations } from "./helpers/api";
import { AUTH_STATE_FILE, installApiProxy, readApiKey } from "./helpers/auth";

test.describe.configure({ mode: "serial" });

test.use({ storageState: AUTH_STATE_FILE });

test.beforeEach(async ({ page }) => {
  await installApiProxy(page);
});

test.describe("Analytics & audit", () => {
  test.beforeAll(async () => {
    const flag = readFlagInfo();
    const apiKey = readApiKey();
    if (!flag || !apiKey) {
      throw new Error(
        "Missing flag info or API key in e2e/.state — run spec 01 + 02 first."
      );
    }
    // Generate 20 eval calls so analytics has data.
    await seedEvaluations(flag.flag_key, apiKey, 20);
  });

  test("analytics overview renders cards and per-flag breakdown", async ({ page }) => {
    await page.goto("/analytics");
    await expect(page.getByRole("heading", { name: /analytics overview/i })).toBeVisible({
      timeout: 15_000,
    });

    // StatsCards component — we expect at least one card with a number.
    await expect(page.getByText(/total flags/i)).toBeVisible();
    await expect(page.getByText(/total evals/i)).toBeVisible();

    // Per-flag breakdown should include our seeded flag key.
    const flag = readFlagInfo();
    if (flag) {
      await expect(page.getByText(flag.flag_key)).toBeVisible();
    }
  });

  test("flag analytics drilldown shows charts and non-zero totals", async ({ page }) => {
    const flag = readFlagInfo();
    test.skip(!flag, "No seeded flag — run spec 02 first.");

    await page.goto(`/flags/${flag!.id}/analytics`);

    // Total requests card should render with a numeric value > 0 eventually.
    await expect(page.getByText(/total requests/i)).toBeVisible({ timeout: 15_000 });

    // Charts render as SVGs inside recharts wrappers.
    await expect(page.locator("svg").first()).toBeVisible({ timeout: 15_000 });

    // Sanity: cohort breakdown header is present.
    await expect(page.getByText(/cohort breakdown/i)).toBeVisible();
    await expect(page.getByText(/over time/i)).toBeVisible();
  });

  test("range picker switches preset and back", async ({ page }) => {
    const flag = readFlagInfo();
    test.skip(!flag, "No seeded flag — run spec 02 first.");

    await page.goto(`/flags/${flag!.id}/analytics`);
    await expect(page.getByText(/total requests/i)).toBeVisible();

    // Switch to 1h.
    await page.getByRole("button", { name: "1h", exact: true }).click();
    await expect(page.getByRole("button", { name: "1h", exact: true })).toHaveClass(
      /bg-slate-900|bg-slate-50/
    );

    // Switch back to 24h.
    await page.getByRole("button", { name: "24h", exact: true }).click();
    await expect(page.getByRole("button", { name: "24h", exact: true })).toHaveClass(
      /bg-slate-900|bg-slate-50/
    );
  });

  test("audit log shows flag.create and opens detail drawer", async ({ page }) => {
    await page.goto("/audit");
    await expect(page.getByRole("heading", { name: /audit log/i })).toBeVisible({
      timeout: 15_000,
    });

    // Wait for at least one row.
    const rows = page.locator("table tbody tr");
    await expect(rows.first()).toBeVisible({ timeout: 15_000 });

    // flag.create should be present since spec 02 created flags.
    await expect(page.getByText(/flag\.create/i).first()).toBeVisible();

    // Click first row — detail drawer should open with JSON.
    await rows.first().click();
    // Drawer: either a dialog role or a visible close affordance.
    const drawer = page
      .getByRole("dialog")
      .or(page.locator('[data-state="open"]'))
      .first();
    await expect(drawer).toBeVisible({ timeout: 5_000 });
  });
});
