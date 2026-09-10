import type { Page } from "@playwright/test";
import { expect } from "@playwright/test";

export const PASSWORD = "uma-password-de-teste";

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Registers a fresh account per test, the same way the API tests do: every
 * assertion then runs against data no other test can have touched. */
export async function signUp(
  page: Page,
  sex: "M" | "F" | "" = "F",
  { heightCm }: { heightCm?: string } = {},
) {
  const email = `e2e-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`;

  await page.goto("/login");
  await page.getByRole("button", { name: "Ainda não tens conta? Criar uma." }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Palavra-passe").fill(PASSWORD);
  await page.getByLabel("Nome").fill("Ana Teste");
  if (sex) await page.getByLabel("Sexo").selectOption(sex);
  if (heightCm) await page.getByLabel("Altura").fill(heightCm);
  await page.getByRole("button", { name: "Criar conta", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Início" })).toBeVisible();
  return { email };
}

/** Records one collection through the manual entry form. */
export async function recordCollection(
  page: Page,
  {
    biomarker,
    value,
    lab = "Synlab Braga",
    collectedOn,
  }: { biomarker: string; value: string; lab?: string; collectedOn?: string },
) {
  await page.goto("/reports");
  await page.getByRole("button", { name: "Registar colheita" }).first().click();

  const form = page.getByRole("dialog");
  if (collectedOn) await form.getByLabel("Data da colheita").fill(collectedOn);
  await form.getByLabel("Laboratório").fill(lab);

  // Search by prefix, then choose the anchored result: a substring match on
  // "Hemoglobina" could also hit a longer, different catalogue label.
  const selector = form.getByRole("combobox", { name: "Biomarcador" });
  await selector.fill(biomarker);
  await form
    .getByRole("option", { name: new RegExp(`^${escapeRegExp(biomarker)}\\s*\\(`) })
    .first()
    .click();

  await form.getByLabel("Valor", { exact: true }).fill(value);
  await form.getByRole("button", { name: "Guardar" }).click();

  await expect(form).toBeHidden();
}

/** Records a weigh-in with a single metric. */
export async function recordScan(page: Page, { metric, value }: { metric: string; value: string }) {
  await page.goto("/body");
  await page.getByRole("button", { name: "Registar pesagem" }).first().click();

  const form = page.getByRole("dialog");
  await form.getByLabel(metric, { exact: true }).fill(value);
  await form.getByRole("button", { name: "Guardar" }).click();

  await expect(form).toBeHidden();
}
