import { test } from "@playwright/test";

import { recordCollection, recordScan, signUp } from "./support";

/**
 * Not an assertion suite: this seeds a realistic account and captures the app so
 * the render can be looked at. Run it with `--grep @shots`; the ordinary e2e run
 * skips it.
 */
test.describe("@shots", () => {
  test("capture the app with real data", async ({ page }, testInfo) => {
    const shot = async (name: string) => {
      await page.waitForTimeout(400); // let entrance motion settle
      await page.screenshot({
        path: `.impeccable/review/${testInfo.project.name}-${name}.png`,
        fullPage: true,
      });
    };

    await signUp(page, "F");

    // Two collections apart in time, so the trend and the sparklines have
    // something real to draw.
    for (const [biomarker, value] of [
      ["Hemoglobina", "11.9"],
      ["Ferritina", "12"],
      ["Colesterol total", "218"],
    ] as const) {
      await recordCollection(page, { biomarker, value, collectedOn: "2026-02-14", lab: "Unilabs" });
    }

    for (const [biomarker, value] of [
      ["Hemoglobina", "10.5"],
      ["Ferritina", "18"],
      ["Vitamina D (25-OH)", "22"],
      ["Colesterol total", "205"],
      ["Colesterol HDL", "61"],
      ["TSH", "2.1"],
    ] as const) {
      await recordCollection(page, { biomarker, value });
    }

    await page.goto("/interventions");
    await page.getByRole("button", { name: "Nova intervenção" }).first().click();
    const intervention = page.getByRole("dialog");
    await intervention.getByLabel("Nome").fill("Ferro bisglicinato");
    await intervention.getByLabel("Dose (opcional)").fill("25 mg/dia");
    await intervention.getByLabel("Início").fill("2020-01-01");
    await intervention.getByRole("button", { name: "Guardar" }).click();

    await recordScan(page, { metric: "IMC (índice de massa corporal)", value: "27.4" });
    await recordScan(page, { metric: "Peso", value: "74.2" });

    await page.goto("/");
    await shot("dashboard");

    await page.getByRole("link", { name: "Hemoglobina", exact: true }).click();
    await shot("biomarker-detail");

    await page.goto("/body");
    await shot("body");

    await page.goto("/reports");
    await shot("reports");

    await page.getByRole("button", { name: "Registar colheita" }).first().click();
    await shot("report-form");
    await page.keyboard.press("Escape");

    await page.goto("/interventions");
    await shot("interventions");

    await page.goto("/profile");
    await shot("profile");

    // The login screen only renders for a signed-out visitor.
    await page.goto("/profile");
    await page.getByRole("button", { name: "Sair" }).click();
    await page.waitForURL(/\/login$/);
    await shot("login");
  });
});
