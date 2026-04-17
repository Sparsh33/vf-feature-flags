import { expect, test } from "@playwright/test";

import { AUTH_STATE_FILE, installApiProxy, readApiKey, writeApiKey } from "./helpers/auth";

test.describe.configure({ mode: "serial" });

test.use({ storageState: AUTH_STATE_FILE });

test.beforeEach(async ({ page }) => {
  await installApiProxy(page);
});

test.describe("Settings", () => {
  test("rotate API key yields a new, different key in the copy-once modal", async ({
    page,
  }) => {
    const previous = readApiKey();
    expect(previous, "Must have captured an API key in spec 01 first").not.toBeNull();

    await page.goto("/settings");
    await expect(page.getByRole("heading", { name: /settings/i })).toBeVisible();

    await page.getByRole("button", { name: /rotate api key/i }).click();

    // Confirmation AlertDialog.
    const confirm = page.getByRole("alertdialog");
    await expect(confirm).toBeVisible();
    await confirm.getByRole("button", { name: /^rotate/i }).click();

    // Copy-once dialog with the new key.
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible({ timeout: 10_000 });

    const keyBox = dialog.locator("div.font-mono").first();
    await expect(keyBox).toBeVisible();
    const newKey = (await keyBox.textContent())?.trim() ?? "";
    expect(newKey.length).toBeGreaterThan(10);
    expect(newKey).not.toEqual(previous);

    // Persist the rotated key so later specs (if rerun) stay consistent.
    writeApiKey(newKey);

    await dialog.getByRole("button", { name: /saved this/i }).click();
  });
});
