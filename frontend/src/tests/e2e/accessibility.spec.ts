import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.describe("Accessibility Audits", () => {
  // Set test timeout to 90 seconds to allow Next.js compiler headroom on dynamic imports
  test.beforeEach(async ({}, testInfo) => {
    testInfo.setTimeout(90000);
  });

  test("should pass accessibility checks on landing root page", async ({ page }) => {
    // Navigates to the local root landing page URL
    await page.goto("/");

    // Injects Axe-core engine and runs WCAG 2.0/2.1 AA audits
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();

    // Asserts zero accessibility violations are present
    expect(results.violations).toEqual([]);
  });

  test("should pass accessibility checks on dashboard home page", async ({ page }) => {
    // Navigates to the main developer dashboard overview
    await page.goto("/dashboard");

    // Injects Axe-core engine and runs WCAG 2.0/2.1 AA audits
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();

    // Asserts zero accessibility violations are present
    expect(results.violations).toEqual([]);
  });

  test("should pass accessibility checks on reports workspace page", async ({ page }) => {
    // Navigates to the dynamic review workspace demo report route
    await page.goto("/dashboard/reports/demo");

    // Injects Axe-core engine and runs WCAG 2.0/2.1 AA audits
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();

    // Asserts zero accessibility violations are present
    expect(results.violations).toEqual([]);
  });

  test("should pass accessibility checks on user settings page", async ({ page }) => {
    // Navigates to the workspace layout settings dashboard route
    await page.goto("/settings");

    // Injects Axe-core engine and runs WCAG 2.0/2.1 AA audits
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();

    // Asserts zero accessibility violations are present
    expect(results.violations).toEqual([]);
  });
});
