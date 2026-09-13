import { expect, test } from "@playwright/test";

// Exercises the real backend + database, same precondition as auth.spec.ts:
// `docker compose up -d postgres backend` (migrations applied) must be running.

const VALID_PASSWORD = "StrongPass1!";

function uniqueEmail(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 100000)}@example.com`;
}

async function registerFreshUser(page: import("@playwright/test").Page, namePrefix: string) {
  const email = uniqueEmail(namePrefix);
  await page.goto("/register");
  await page.getByLabel("Full name").fill(`${namePrefix} User`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(VALID_PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  return email;
}

test.describe("ticket creation and details (Flow 4)", () => {
  test("create a ticket, land on its detail page, and see it in My Tickets", async ({ page }) => {
    await registerFreshUser(page, "ticket-flow");

    const uniqueTitle = `E2E ticket ${Date.now()}`;

    await page.goto("/tickets/new");
    await page.getByLabel("Title").fill(uniqueTitle);
    await page
      .getByLabel("Description")
      .fill("Created by the Flow 4 Playwright test — safe to ignore.");
    await page.getByLabel("Category").selectOption("NETWORK");
    await page.getByLabel("Priority").selectOption("HIGH");
    await page.getByRole("button", { name: "Submit ticket" }).click();

    // Submitting navigates straight to the new ticket's detail page.
    await expect(page).toHaveURL(/\/tickets\/[0-9a-f-]{36}$/);
    await expect(page.getByRole("heading", { name: uniqueTitle })).toBeVisible();
    await expect(page.getByText("Open", { exact: true })).toBeVisible();
    await expect(page.getByText("Unassigned")).toBeVisible();

    // The ticket also shows up in the employee's own list.
    await page.goto("/tickets");
    await expect(page.getByRole("link", { name: new RegExp(uniqueTitle) })).toBeVisible();
  });

  test("validation: empty title/description is rejected client-side", async ({ page }) => {
    await registerFreshUser(page, "ticket-validation");

    await page.goto("/tickets/new");
    await page.getByRole("button", { name: "Submit ticket" }).click();

    // The form never navigates away — required-field validation blocks submission.
    await expect(page).toHaveURL(/\/tickets\/new$/);
  });

  test("posting a comment on a ticket appears immediately", async ({ page }) => {
    await registerFreshUser(page, "ticket-comment");
    const uniqueTitle = `E2E comment ticket ${Date.now()}`;

    await page.goto("/tickets/new");
    await page.getByLabel("Title").fill(uniqueTitle);
    await page.getByLabel("Description").fill("Testing comments end to end.");
    await page.getByRole("button", { name: "Submit ticket" }).click();
    await expect(page).toHaveURL(/\/tickets\/[0-9a-f-]{36}$/);

    const commentText = `A test comment ${Date.now()}`;
    await page.getByPlaceholder("Add a comment...").fill(commentText);
    await page.getByRole("button", { name: "Post comment" }).click();

    await expect(page.getByText(commentText)).toBeVisible();
  });
});
