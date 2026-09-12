import { expect, test } from "@playwright/test";

test("dashboard loads and shows the platform title", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /AI-Powered IT Knowledge/i })).toBeVisible();
});
