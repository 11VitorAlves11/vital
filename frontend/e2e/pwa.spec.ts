import { expect, test } from "@playwright/test";

test("@pwa leaves API and authentication navigations to the server", async ({ page }) => {
  await page.goto("/login");

  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
    if (!navigator.serviceWorker.controller) {
      await new Promise<void>((resolve) => {
        navigator.serviceWorker.addEventListener("controllerchange", () => resolve(), {
          once: true,
        });
      });
    }
  });

  const apiResponse = await page.goto("/api/health");
  expect(apiResponse?.headers()["content-type"]).toContain("application/json");
  await expect(page.locator("body")).toHaveText('{"status":"ok"}');

  const authResponse = await page.goto("/auth/login");
  expect(authResponse?.status()).toBe(404);
  expect(authResponse?.headers()["content-type"]).toContain("application/json");
  await expect(page.locator("body")).toContainText("AUTH_MODE is not 'oidc'");
});
