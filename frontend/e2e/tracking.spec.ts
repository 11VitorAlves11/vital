import { expect, test } from "@playwright/test";

import { recordCollection, recordScan, signUp } from "./support";

test.describe("recording and reading values", () => {
  test("a collection below the female range is flagged low on the dashboard", async ({ page }) => {
    await signUp(page, "F");
    // 10,5 g/dL against the catalogue's female range of 12–15.
    await recordCollection(page, { biomarker: "Hemoglobina", value: "10.5" });

    await page.goto("/");
    const card = page.locator("div").filter({ hasText: "Hemoglobina" }).last();
    await expect(page.getByRole("heading", { name: "Hematologia" })).toBeVisible();
    await expect(card.getByText("Baixo")).toBeVisible();
    await expect(page.getByText("10,5")).toBeVisible();
  });

  test("the biomarker page draws the band and the intervention overlay", async ({ page }) => {
    await signUp(page, "F");
    await recordCollection(page, { biomarker: "Hemoglobina", value: "13.2" });

    await page.goto("/interventions");
    await page.getByRole("button", { name: "Nova intervenção" }).first().click();
    const form = page.getByRole("dialog");
    await form.getByLabel("Nome").fill("Ferro bisglicinato");
    await form.getByLabel("Início").fill("2020-01-01");
    await form.getByRole("button", { name: "Guardar" }).click();
    await expect(form).toBeHidden();

    await page.goto("/");
    await page.getByRole("link", { name: "Hemoglobina", exact: true }).click();

    const chart = page.getByRole("img", { name: /Hemoglobina/ });
    await expect(chart).toBeVisible();
    // The limits are drawn as labelled lines, not only as shading.
    await expect(chart.locator("text=Mín.").first()).toBeVisible();
    await expect(page.getByText("Ferro bisglicinato").first()).toBeVisible();
    // The history is the chart's textual alternative, so it ships with it.
    await expect(page.getByText("Synlab Braga").first()).toBeVisible();
  });

  test("a weigh-in is classified by the clinical bands, and only where they exist", async ({
    page,
  }) => {
    await signUp(page, "F");
    await recordScan(page, { metric: "IMC (índice de massa corporal)", value: "27" });

    await expect(page.getByText("Pré-obesidade")).toBeVisible();

    await recordScan(page, { metric: "Peso", value: "74.2" });
    await expect(page.getByText("Sem referência clínica").first()).toBeVisible();
  });

  test("interventions can be ended", async ({ page }) => {
    await signUp(page);
    await page.goto("/interventions");
    await page.getByRole("button", { name: "Nova intervenção" }).first().click();

    const form = page.getByRole("dialog");
    await form.getByLabel("Nome").fill("Creatina");
    await form.getByRole("button", { name: "Guardar" }).click();
    await expect(form).toBeHidden();

    await expect(page.getByText("Em curso")).toBeVisible();
    await page.getByRole("button", { name: "Terminar" }).click();
    await expect(page.getByText("Em curso")).toBeHidden();
  });

  test("a profile without a sex is told why nothing is classified", async ({ page }) => {
    await signUp(page, "");
    await page.goto("/body");
    await expect(page.getByText("Indica o sexo no perfil")).toBeVisible();

    await page.goto("/profile");
    await page.getByLabel("Sexo").selectOption("F");
    await page.getByRole("button", { name: "Guardar" }).click();

    await page.goto("/body");
    await expect(page.getByText("Indica o sexo no perfil")).toBeHidden();
  });
});
