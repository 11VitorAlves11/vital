import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import { VitePWA } from "vite-plugin-pwa";

// In Docker the API is reachable as http://api:8000; locally as http://localhost:8000.
const apiTarget = process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "Vital",
        short_name: "Vital",
        description: "Tracking de biomarcadores e composição corporal",
        lang: "pt-PT",
        theme_color: "#155BC4",
        background_color: "#F3F6FB",
        display: "standalone",
        start_url: "/",
        icons: [{ src: "/icon.png", sizes: "512x512", type: "image/png", purpose: "any maskable" }],
      },
    }),
  ],
  server: {
    port: 5173,
    // The dev server refuses any Host it does not know. The e2e run reaches it
    // as http://web:5173 from inside the compose network, which is that case.
    allowedHosts: ["web"],
    watch: {
      // Test output and tooling caches are not sources. Watching them makes the
      // dev server reload the page mid-run, which aborts whatever the test had
      // in flight and reads as a flaky failure.
      ignored: ["**/test-results/**", "**/playwright-report/**", "**/.impeccable/**"],
    },
    proxy: {
      "/api": { target: apiTarget, changeOrigin: true },
      "/auth": { target: apiTarget, changeOrigin: true },
    },
  },
  // The e2e suite targets the built app, not the dev server: no HMR reloading a
  // page mid-test and no StrictMode double-effects, so a failure means a defect.
  preview: {
    port: 5173,
    allowedHosts: ["web"],
    proxy: {
      "/api": { target: apiTarget, changeOrigin: true },
      "/auth": { target: apiTarget, changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    // e2e/ belongs to Playwright, which runs a browser against the real stack.
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
