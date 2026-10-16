import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

// Executa a base consolidada em uma porta propria, sem reutilizar outro Vite.
export default defineConfig({
  ...base,
  workers: 2,
  use: { ...base.use, baseURL: "http://127.0.0.1:5196" },
  webServer: {
    command: "npm run dev -- --host 127.0.0.1 --port 5196 --strictPort",
    url: "http://127.0.0.1:5196",
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
