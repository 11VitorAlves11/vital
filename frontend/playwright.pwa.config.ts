import { defineConfig, devices } from "@playwright/test";

/**
 * Production-only checks for behaviour owned by the generated service worker.
 * The regular suite uses the dev server, where Vite deliberately has no active
 * service worker and therefore cannot catch navigation-fallback regressions.
 */
export default defineConfig({
  testDir: "./e2e",
  outputDir: "/tmp/vital-playwright-pwa",
  grep: /@pwa/,
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: "http://localhost:4173",
    ...devices["Desktop Chrome"],
    serviceWorkers: "allow",
  },
  webServer: {
    command: "npm run build && npm run preview -- --host 127.0.0.1 --port 4173",
    url: "http://localhost:4173/login",
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
