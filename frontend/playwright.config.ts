import { defineConfig, devices } from "@playwright/test";

/**
 * The suite runs against the real stack from docker-compose.dev.yml, not a mock:
 * the flags it asserts are computed server-side, so a mocked API would be testing
 * the fixtures rather than the product.
 *
 * E2E_BASE_URL points at the web container from inside the Playwright image
 * (http://web:5173) and at the published port from the host.
 */
const baseURL = process.env.E2E_BASE_URL ?? "http://localhost:5173";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [["github"], ["list"]] : [["list"]],
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    locale: "pt-PT",
    timezoneId: "Europe/Lisbon",
  },
  projects: [
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } },
    },
    {
      // The breakpoint switch is a real behaviour, so it gets a real device.
      name: "mobile",
      use: { ...devices["Pixel 7"] },
    },
  ],
});
