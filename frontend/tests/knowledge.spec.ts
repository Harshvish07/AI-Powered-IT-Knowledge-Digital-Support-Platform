import { expect, test } from "@playwright/test";

// Knowledge base search (frontend-testing checklist item #6). Uploading
// requires ADMIN — see admin.spec.ts for why these tests read a seeded
// admin's credentials from the environment and skip if they aren't set.
// The test uploads its own uniquely-titled document rather than relying on
// the demo knowledge base being seeded, so it's self-contained; if
// GEMINI_API_KEY isn't configured in this environment the upload will land
// on FAILED instead of READY, and the test skips rather than failing on
// what would be an environment/config issue, not a code defect.

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL;
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD;

test.describe("knowledge base search", () => {
  test.beforeEach(() => {
    test.skip(
      !ADMIN_EMAIL || !ADMIN_PASSWORD,
      "Set E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD (a seeded admin account) to run this spec.",
    );
  });

  test("a newly uploaded document is findable by search, and unrelated searches find nothing", async ({
    page,
  }) => {
    const uniqueTitle = `E2E Search Target ${Date.now()}`;

    await page.goto("/login");
    await page.getByLabel("Email").fill(ADMIN_EMAIL!);
    await page.getByLabel("Password").fill(ADMIN_PASSWORD!);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL(/\/dashboard$/);

    await page.goto("/knowledge/upload");
    await page.setInputFiles('input[type="file"]', {
      name: "e2e-search-target.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(
        "This document exists only to verify that the knowledge base search box works.",
      ),
    });
    await page.getByLabel("Title").fill(uniqueTitle);
    await page.getByLabel("Category").fill("E2E Testing");
    await page.getByRole("button", { name: "Upload" }).click();

    await expect(page).toHaveURL(/\/knowledge\/[0-9a-f-]{36}$/);

    const readyBadge = page.getByText("READY", { exact: true });
    const failedBadge = page.getByText("FAILED", { exact: true });
    await Promise.race([
      readyBadge.waitFor({ timeout: 30_000 }).catch(() => undefined),
      failedBadge.waitFor({ timeout: 30_000 }).catch(() => undefined),
    ]);

    if (await failedBadge.isVisible().catch(() => false)) {
      test.skip(
        true,
        "Document processing failed (likely no GEMINI_API_KEY configured) — not a search-UI issue.",
      );
      return;
    }
    await expect(readyBadge).toBeVisible();

    // Now verify the search box actually filters by this document.
    await page.goto("/knowledge");
    const searchBox = page.getByPlaceholder("Search documents...");

    await searchBox.fill(uniqueTitle);
    await expect(page.getByRole("link", { name: new RegExp(uniqueTitle) })).toBeVisible();

    await searchBox.fill("zzz-definitely-not-a-real-document-zzz");
    await expect(page.getByText("No documents found.")).toBeVisible();
  });
});
