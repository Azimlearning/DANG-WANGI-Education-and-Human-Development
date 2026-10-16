import { defineConfig } from "vitest/config";

export default defineConfig({
  esbuild: { jsx: "automatic" },
  test: { environment: "jsdom", include: ["lib/**/*.test.{ts,tsx}", "components/**/*.test.{ts,tsx}"] },
});
