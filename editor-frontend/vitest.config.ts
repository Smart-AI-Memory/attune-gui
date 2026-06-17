import { defineConfig } from "vitest/config";

// Unit tests live next to source. The e2e specs under `e2e/` use
// `@playwright/test` syntax, so they're explicitly excluded here and
// run via `npm run e2e` instead.
//
// This project also covers the Cowork dashboard's no-build ES modules
// served from sidecar/attune_gui/static_cw/ — one Vitest project + one
// CI job for all attune-gui frontend JS (editor + dashboard).
export default defineConfig({
  test: {
    include: [
      "src/**/*.test.ts",
      "../sidecar/attune_gui/static_cw/**/*.test.js",
    ],
    exclude: ["node_modules", "e2e"],
  },
});
