import { expect, test } from "@playwright/test";

import { PASSWORD, signUp } from "./support";

test.describe("local authentication", () => {
  test("register, sign out, sign back in", async ({ page }) => {
    const { email } = await signUp(page);

    await page.goto("/profile");
    await page.getByRole("button", { name: "Sair" }).click();
    await expect(page).toHaveURL(/\/login$/);

    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Palavra-passe").fill(PASSWORD);
    await page.getByRole("button", { name: "Entrar", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Início" })).toBeVisible();
  });

  test("a wrong password is reported on the form", async ({ page }) => {
    const { email } = await signUp(page);
    await page.goto("/profile");
    await page.getByRole("button", { name: "Sair" }).click();

    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Palavra-passe").fill("errada-de-certeza");
    await page.getByRole("button", { name: "Entrar", exact: true }).click();

    await expect(page.getByRole("alert")).toHaveText("Email ou palavra-passe inválidos.");
  });

  test("a signed-out visitor cannot reach the data", async ({ page }) => {
    for (const path of ["/", "/reports", "/body", "/interventions", "/profile"]) {
      await page.goto(path);
      await expect(page).toHaveURL(/\/login$/);
    }
  });

  test("the session survives a reload", async ({ page }) => {
    await signUp(page);
    await page.reload();
    await expect(page.getByRole("heading", { name: "Início" })).toBeVisible();
  });
});
