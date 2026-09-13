import { expect, test } from "@playwright/test";

// These tests exercise the real backend + database (via NEXT_PUBLIC_API_BASE_URL),
// so `docker compose up -d postgres backend` (with migrations applied) must be
// running before `npm run test:e2e`. See README.md.

const VALID_PASSWORD = "StrongPass1!";

function uniqueEmail(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 100000)}@example.com`;
}

test.describe("authentication", () => {
  test("protected route redirects to login when signed out", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("register lands on the dashboard, then logout blocks it again", async ({ page }) => {
    const email = uniqueEmail("register");

    await page.goto("/register");
    await page.getByLabel("Full name").fill("E2E Test User");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(VALID_PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();

    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByRole("heading", { name: /AI-Powered IT Knowledge/i })).toBeVisible();
    await expect(page.getByText("E2E Test User", { exact: true })).toBeVisible();
    await expect(page.getByText(email)).toBeVisible();

    await page.getByRole("button", { name: "Log out" }).click();
    await expect(page).toHaveURL(/\/login$/);

    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("login with existing credentials reaches the dashboard", async ({ page }) => {
    const email = uniqueEmail("login");

    await page.goto("/register");
    await page.getByLabel("Full name").fill("Login Test User");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(VALID_PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/dashboard$/);

    await page.getByRole("button", { name: "Log out" }).click();
    await expect(page).toHaveURL(/\/login$/);

    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(VALID_PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByText("Login Test User", { exact: true })).toBeVisible();
  });

  test("login with the wrong password shows an error and stays on /login", async ({ page }) => {
    const email = uniqueEmail("wrongpass");

    await page.goto("/register");
    await page.getByLabel("Full name").fill("Wrong Pass User");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(VALID_PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/dashboard$/);

    await page.getByRole("button", { name: "Log out" }).click();
    await expect(page).toHaveURL(/\/login$/);

    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill("TotallyWrong1!");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page).toHaveURL(/\/login$/);
  });
});
