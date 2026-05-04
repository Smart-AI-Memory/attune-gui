import { defineConfig } from "vitest/config";

// Unit tests live next to source. The e2e specs under `e2e/` use
// `@playwright/test` syntax, so they're explicitly excluded here and
// run via `npm run e2e` instead.
export default defineConfig({
  test: {
    include: ["src/**/*.test.ts"],
    exclude: ["node_modules", "e2e"],
  },
});
