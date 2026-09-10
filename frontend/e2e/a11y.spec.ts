import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";
import { expect, test } from "@playwright/test";

import { recordCollection, signUp } from "./support";

/** Zero critical or serious violations is the release gate, not a target. */
async function scan(page: Page) {
  const { violations } = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();

  const blocking = violations.filter(
    (violation) => violation.impact === "critical" || violation.impact === "serious",
  );
  return blocking.map((violation) => ({
    id: violation.id,
    impact: violation.impact,
    nodes: violation.nodes.map((node) => node.target.join(" ")),
  }));
}

test.describe("accessibility", () => {
  test("login", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByLabel("Email")).toBeVisible();
    expect(await scan(page)).toEqual([]);
  });

  test("dashboard with data", async ({ page }) => {
    await signUp(page, "F");
    await recordCollection(page, { biomarker: "Hemoglobina", value: "10.5" });
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Desde a última colheita" })).toBeVisible();
    expect(await scan(page)).toEqual([]);
  });

  test("biomarker detail", async ({ page }) => {
    await signUp(page, "F");
    await recordCollection(page, { biomarker: "Hemoglobina", value: "13.2" });
    await page.goto("/");
    await page.getByText("Hematologia", { exact: true }).click();
    await page.getByRole("link", { name: "Hemoglobina", exact: true }).click();
    await expect(page.getByRole("img", { name: /Hemoglobina/ })).toBeVisible();
    expect(await scan(page)).toEqual([]);
  });

  test("the weigh-in form, which is the densest surface in the app", async ({ page }) => {
    await signUp(page, "F");
    await page.goto("/body");
    await page.getByRole("button", { name: "Registar pesagem" }).first().click();
    await expect(page.getByRole("dialog")).toBeVisible();
    expect(await scan(page)).toEqual([]);
  });

  test("every interactive element on the dashboard is reachable by keyboard", async ({ page }) => {
    await signUp(page, "F");
    await recordCollection(page, { biomarker: "Hemoglobina", value: "13.2" });
    await page.goto("/");

    await page.keyboard.press("Tab");
    const focused = await page.evaluate(() => {
      const element = document.activeElement;
      if (!element) return null;
      const ring = getComputedStyle(element, ":focus-visible").outlineWidth;
      return { tag: element.tagName, ring };
    });
    expect(focused).not.toBeNull();
    // One global :focus-visible rule; no primitive may drop it.
    expect(focused?.ring).not.toBe("0px");
  });
});
