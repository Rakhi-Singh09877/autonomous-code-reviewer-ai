import { test, expect } from "@playwright/test";

test.describe("Frontend E2E Smoke Tests", () => {
  test("should successfully load the workspace shell layout and verify title", async ({ page }) => {
    // Navigates to local base URL configured in playwright.config.ts
    await page.goto("/");

    // Asserts page title matches layout metadata configuration
    await expect(page).toHaveTitle("Autonomous Code Reviewer AI");

    // Asserts brand headers are visible
    const brandHeader = page.locator("text=Autonomous Reviewer AI");
    await expect(brandHeader).toBeVisible();

    // Asserts layout main slots display workspace placeholder content
    const heading = page.locator("h1");
    await expect(heading).toHaveText("Workspace Overview");
  });
});
