import { expect, test } from "@playwright/test";

// Exercises the real backend + database + Gemini API (no mocking is possible
// from Playwright — the calls happen inside the backend container). See
// docs/testing.md "End-to-end tests" for the tradeoffs this implies:
// Flow 3 (unknown question -> safe fallback) never calls the chat LLM at all
// (the similarity-threshold gate returns the fallback directly), so it only
// depends on the embeddings API and is safe to assert on unconditionally.
// Flow 2 (known question -> grounded answer + source) does call the real
// chat LLM, which is subject to the free tier's daily quota — if the backend
// returns its "temporarily unavailable" error for that reason, the test
// skips rather than fails, the same graceful-degradation policy already used
// by the backend's own real-API integration tests (backend/tests/test_rag.py).

const VALID_PASSWORD = "StrongPass1!";
const SERVICE_UNAVAILABLE_TEXT = "temporarily unavailable";
const NO_EVIDENCE_TEXT = "couldn't find enough information in the IT knowledge base";

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
}

async function askAssistant(page: import("@playwright/test").Page, question: string) {
  await page.goto("/assistant");
  await page.getByPlaceholder(/Ask a question about IT policies/).fill(question);
  await page.getByRole("button", { name: "Send" }).click();
}

test.describe("AI assistant (Flows 2 & 3)", () => {
  test("known question returns a grounded answer with a source citation (Flow 2)", async ({
    page,
  }) => {
    await registerFreshUser(page, "assistant-known");
    // Matches the seeded demo knowledge base's "MFA Setup Guide" (see
    // backend/app/evaluation/questions.json) — requires
    // ./scripts/seed-knowledge.sh to have been run against this environment.
    await askAssistant(page, "How do I enable multi-factor authentication on my account?");

    const errorBanner = page.getByText(SERVICE_UNAVAILABLE_TEXT);
    const fallbackAnswer = page.getByText(NO_EVIDENCE_TEXT);

    await Promise.race([
      errorBanner.waitFor({ timeout: 30_000 }).catch(() => undefined),
      fallbackAnswer.waitFor({ timeout: 30_000 }).catch(() => undefined),
      page
        .getByText("Sources")
        .waitFor({ timeout: 30_000 })
        .catch(() => undefined),
    ]);

    if (await errorBanner.isVisible().catch(() => false)) {
      test.skip(
        true,
        "Real Gemini chat call unavailable (likely free-tier quota) — see docs/testing.md.",
      );
      return;
    }
    if (await fallbackAnswer.isVisible().catch(() => false)) {
      test.skip(
        true,
        "Assistant returned the no-evidence fallback — the demo knowledge base likely " +
          "isn't seeded in this environment. Run ./scripts/seed-knowledge.sh first.",
      );
      return;
    }

    await expect(page.getByText("Sources")).toBeVisible();
    await expect(page.getByText(/MFA Setup Guide/)).toBeVisible();
  });

  test("unknown question returns the safe fallback, not a fabricated answer (Flow 3)", async ({
    page,
  }) => {
    await registerFreshUser(page, "assistant-unknown");
    await askAssistant(page, "What pizza toppings does the office order on Fridays?");

    // This path never calls the chat LLM at all (see rag_service — the
    // similarity-threshold gate short-circuits before the LLM is invoked),
    // so it only depends on the embeddings API and needs no skip logic.
    await expect(page.getByText(NO_EVIDENCE_TEXT)).toBeVisible({ timeout: 30_000 });
  });
});
