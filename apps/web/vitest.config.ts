import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    include: ["src/**/*.test.{ts,tsx}"],
    exclude: ["e2e/**", "node_modules/**"],
    coverage: {
      provider: "v8",
      reporter: ["text", "text-summary"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.test.{ts,tsx}",
        "src/test/**",
        "src/main.tsx",
        "src/vite-env.d.ts",
        // Landing visual lock — do not push coverage-driven edits here.
        "src/Landing.tsx",
        "src/landing.css",
      ],
      // Incremental floor: raise as studio/unit coverage grows.
      thresholds: {
        lines: 55,
        functions: 35,
        branches: 55,
        statements: 55,
      },
    },
  },
});
