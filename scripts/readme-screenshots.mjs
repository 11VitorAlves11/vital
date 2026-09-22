// Run from the repository root: node scripts/readme-screenshots.mjs
// Requires the local development stack with SEED_DEMO_DATA=true and Playwright Chromium.
import { mkdir } from "node:fs/promises";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(new URL("../frontend/package.json", import.meta.url));
const { chromium, expect } = require("@playwright/test");
const output = fileURLToPath(new URL("../.github/images/", import.meta.url));
await mkdir(output, { recursive: true });
const browser = await chromium.launch();

try {
  for (const mobile of [false, true]) {
    const context = await browser.newContext({
      baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173",
      viewport: mobile ? { width: 390, height: 844 } : { width: 1440, height: 1000 },
      deviceScaleFactor: 1,
      isMobile: mobile,
      hasTouch: mobile,
      locale: "en-GB",
      timezoneId: "Europe/Lisbon",
      colorScheme: "light",
      reducedMotion: "reduce",
    });
    await context.addInitScript(() => {
      localStorage.setItem("vital.language", "en");
      localStorage.setItem("vital-theme", "light");
    });
    const page = await context.newPage();
    const failures = [];
    page.on("pageerror", (error) => failures.push(error.message));
    page.on("response", (response) => {
      if (response.status() >= 500) failures.push(`${response.status()} ${response.url()}`);
    });
    await page.goto("/login");
    await page.getByLabel("Email", { exact: true }).fill("demo@example.com");
    await page.getByLabel("Password", { exact: true }).fill("VitalDemo2026!");
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Home", exact: true })).toBeVisible();

    async function capture(name) {
      await page.waitForLoadState("networkidle");
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({ path: `${output}${name}.png`, animations: "disabled" });
      console.log(`Captured ${name}`);
    }

    if (mobile) {
      for (const [route, heading, name] of [
        ["/", "Home", "mobile-dashboard"],
        ["/timeline", "Timeline", "mobile-timeline"],
        ["/body", "Body composition", "mobile-body"],
      ]) {
        await page.goto(route);
        await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
        await capture(name);
      }
    } else {
      await capture("desktop-dashboard");
      await page.getByRole("button", { name: "Use dark theme" }).click();
      await capture("desktop-dark");
      await page.goto("/");
      await page.locator('a[href^="/biomarkers/"]').first().click();
      await expect(page.locator(".recharts-surface").first()).toBeVisible();
      await capture("desktop-trend");
    }
    if (failures.length) throw new Error(failures.join("\n"));
    await context.close();
  }
} finally {
  await browser.close();
}
