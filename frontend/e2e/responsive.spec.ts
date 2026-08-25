import { expect, test } from "@playwright/test";

import { signUp } from "./support";

test.describe("navigation adapts to the viewport", () => {
  test("bottom bar on a phone, sidebar on a desktop — never both", async ({ page }) => {
    await signUp(page);

    const nav = page.getByRole("navigation", { name: "Navegação principal" });
    await expect(nav).toHaveCount(1);

    await page.setViewportSize({ width: 390, height: 844 });
    await expect(nav).toHaveCSS("position", "fixed");

    await page.setViewportSize({ width: 1280, height: 900 });
    await expect(nav).toHaveCount(1);
    await expect(nav).not.toHaveCSS("position", "fixed");
  });

  test("every destination carries its label", async ({ page }) => {
    await signUp(page);
    for (const label of ["Início", "Análises", "Corpo", "Intervenções", "Perfil"]) {
      await expect(page.getByRole("link", { name: label })).toBeVisible();
    }
  });

  test("touch targets on the phone clear 44px", async ({ page }) => {
    await signUp(page);
    await page.setViewportSize({ width: 390, height: 844 });

    const nav = page.getByRole("navigation", { name: "Navegação principal" });
    // The shell swaps the sidebar for the bottom bar on a media-query event, so
    // the measurement has to wait for that swap rather than race it.
    await expect(nav).toHaveCSS("position", "fixed");

    const links = nav.getByRole("link");
    for (const link of await links.all()) {
      const box = await link.boundingBox();
      expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
    }
  });

  test("the page never scrolls sideways", async ({ page }) => {
    await signUp(page);
    for (const width of [390, 768, 1280]) {
      await page.setViewportSize({ width, height: 900 });
      const overflows = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
      );
      expect(overflows, `horizontal scroll at ${width}px`).toBe(false);
    }
  });
});
