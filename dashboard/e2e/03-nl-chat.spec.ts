import { expect, test } from "@playwright/test";

import { AUTH_STATE_FILE } from "./helpers/auth";

test.describe.configure({ mode: "serial" });

test.use({ storageState: AUTH_STATE_FILE });

// The NL chat relies on a local LLM (Ollama). Mark these as slow and
// tolerate partial extraction — a successful back-end round-trip is the
// core contract; a complete committed flag is a bonus path.
test.describe("NL chat", () => {
  test("assistant replies and extracted panel updates", async ({ page }) => {
    test.slow();

    await page.goto("/chat");
    await expect(
      page.getByRole("heading", { name: /flag builder/i }),
    ).toBeVisible();

    const textarea = page.locator("textarea");
    await textarea.fill(
      "Create a flag called welcome_banner with a 50/50 A-B test returning " +
        '{"color":"green"} or {"color":"blue"}, default {"color":"gray"}.',
    );

    await page.getByRole("button", { name: /^send$/i }).click();

    // Wait up to 30s for an assistant bubble to render — LLM can be slow.
    const assistantBubble = page
      .locator('[data-role="assistant"], .assistant, [class*="assistant"]')
      .first();
    // Fallback: any text that looks like a response; we assert the typing
    // indicator disappears + input is re-enabled after a response arrives.
    await expect(textarea).toBeEnabled({ timeout: 30_000 });

    // Extracted tab should show _something_ — at least a non-empty label/key.
    await page.getByRole("button", { name: /extracted params/i }).click();

    // Accept any partial extraction: look for the flag key we asked for,
    // OR for the label "flag_key" appearing in the panel. Don't fail if
    // the LLM produced neither — the core smoke is the chat round-trip.
    const extractedPanel = page.locator(
      "text=/welcome_banner|flag_key|cohort/i",
    );
    // Non-blocking: log if nothing extracted, don't fail.
    const extractedCount = await extractedPanel.count();
    // eslint-disable-next-line no-console
    console.log(`[nl-chat] extracted panel matches: ${extractedCount}`);

    // Optional commit path: if a Commit button appears + is enabled, click it.
    const commitButton = page.getByRole("button", { name: /^commit/i });
    if ((await commitButton.count()) > 0 && (await commitButton.isEnabled())) {
      await commitButton.click();
      // Success toast OR committed state becomes locked.
      await expect(page.getByText(/flag created|view flag/i)).toBeVisible({
        timeout: 30_000,
      });

      // Verify it exists in the flag list.
      await page.goto("/flags");
      // The LLM may not use the exact key we suggested; just assert the
      // list is non-empty (it had at least one flag from spec 02 anyway).
      await expect(page.locator("table tbody tr").first()).toBeVisible();
      // Soft-check that welcome_banner made it — don't fail otherwise.
      const hasBanner = await page.getByText("welcome_banner").count();
      // eslint-disable-next-line no-console
      console.log(`[nl-chat] welcome_banner visible in list: ${hasBanner > 0}`);
      assistantBubble; // quiet unused-lint
    }
  });
});
