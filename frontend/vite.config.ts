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
        theme_color: "#0D7377",
        background_color: "#FAFAF8",
        display: "standalone",
        start_url: "/",
        icons: [{ src: "/icon.png", sizes: "512x512", type: "image/png", purpose: "any maskable" }],
      },
    }),
  ],
  server: {
    port: 5173,
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
  },
});
