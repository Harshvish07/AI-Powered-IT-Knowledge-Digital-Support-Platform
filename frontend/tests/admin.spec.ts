import { expect, test } from "@playwright/test";

// Flow 5 needs an ADMIN account, and there is no self-service way to create
// one (by design — see README.md "Seeding an admin user"). This spec reads
// credentials for an already-seeded admin from the environment and skips
// entirely if they aren't provided, rather than failing:
//
//   E2E_ADMIN_EMAIL=admin@example.com E2E_ADMIN_PASSWORD=... npm run test:e2e
//
// The ticket these tests manage is created by the test itself (a fresh
// employee registration + ticket, done through the UI) so the admin flow is
// self-contained and doesn't depend on any other data already existing.

const VALID_PASSWORD = "StrongPass1!";
const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL;
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD;

function uniqueEmail(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 100000)}@example.com`;
}

test.describe("admin dashboard and ticket management (Flow 5)", () => {
  test.beforeEach(() => {
    test.skip(
      !ADMIN_EMAIL || !ADMIN_PASSWORD,
      "Set E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD (a seeded admin account) to run this spec.",
    );
  });

  test("admin logs in, views the dashboard, then assigns and updates a ticket", async ({
    page,
  }) => {
    // 1. Create a ticket as a fresh employee, self-contained (no dependency
    // on any pre-existing ticket data).
    const employeeEmail = uniqueEmail("admin-flow-employee");
    const uniqueTitle = `E2E admin-flow ticket ${Date.now()}`;

    await page.goto("/register");
    await page.getByLabel("Full name").fill("Admin Flow Employee");
    await page.getByLabel("Email").fill(employeeEmail);
    await page.getByLabel("Password").fill(VALID_PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/dashboard$/);

    await page.goto("/tickets/new");
    await page.getByLabel("Title").fill(uniqueTitle);
    await page.getByLabel("Description").fill("Created by the Flow 5 Playwright test.");
    await page.getByRole("button", { name: "Submit ticket" }).click();
    await expect(page).toHaveURL(/\/tickets\/[0-9a-f-]{36}$/);

    await page.getByRole("button", { name: "Log out" }).click();
    await expect(page).toHaveURL(/\/login$/);

    // 2. Admin login -> dashboard.
    await page.getByLabel("Email").fill(ADMIN_EMAIL!);
    await page.getByLabel("Password").fill(ADMIN_PASSWORD!);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL(/\/dashboard$/);

    await page.goto("/admin");
    await expect(page.getByRole("heading", { name: "Admin Dashboard" })).toBeVisible();
    await expect(page.getByText("Total tickets")).toBeVisible();

    // 3. View the ticket via the admin ticket list.
    await page.goto("/admin/tickets");
    await page.getByPlaceholder("Search tickets...").fill(uniqueTitle);
    await page.getByRole("link", { name: new RegExp(uniqueTitle) }).click();
    await expect(page).toHaveURL(/\/admin\/tickets\/[0-9a-f-]{36}$/);
    await expect(page.getByRole("heading", { name: uniqueTitle })).toBeVisible();

    // 4. Assign the ticket (to whichever user the dropdown lists first) and
    // change its status.
    const assignedToSelect = page.getByLabel("Assigned to");
    await assignedToSelect.selectOption({ index: 1 });
    await expect(assignedToSelect).not.toHaveValue("");

    const statusSelect = page.getByLabel("Status");
    await statusSelect.selectOption("IN_PROGRESS");
    await expect(statusSelect).toHaveValue("IN_PROGRESS");
    await expect(page.getByText("In Progress", { exact: true })).toBeVisible();
  });
});
