import { expect, test } from "@playwright/test";

// As of Phase 2, "/" is an auth-aware redirect (see app/page.tsx) rather than the
// dashboard itself — the dashboard now lives at /dashboard and requires sign-in.
// The platform title is covered on the authenticated dashboard in tests/auth.spec.ts.
test("root redirects to /login when signed out", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
});
