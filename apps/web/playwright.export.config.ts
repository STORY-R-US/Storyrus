import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

// Valida o build da exportacao sem depender da compilacao sob demanda do Vite.
export default defineConfig({
  ...base,
  workers: 1,
  use: { ...base.use, baseURL: "http://127.0.0.1:5197" },
  webServer: {
    command: "npm run preview -- --host 127.0.0.1 --port 5197 --strictPort",
    url: "http://127.0.0.1:5197",
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
