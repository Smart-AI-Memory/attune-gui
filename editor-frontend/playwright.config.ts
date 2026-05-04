/**
 * Playwright config for the four golden editor flows.
 *
 * Spawns the sidecar (Python) once per test run with an isolated
 * corpora registry under `e2e/.tmp/`. Each test wipes/registers its
 * own corpus so they don't see each other's state.
 *
 * Run locally:
 *   npm run e2e
 *   npm run e2e:headed   # see the browser
 *   npm run e2e:ui       # Playwright UI mode
 */

import { defineConfig } from "@playwright/test";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const TMP_DIR = resolve(HERE, "e2e/.tmp");
const REGISTRY_PATH = resolve(TMP_DIR, "corpora.json");
const SIDECAR_PORT = process.env.E2E_SIDECAR_PORT ?? "8773";
const SIDECAR_URL = `http://127.0.0.1:${SIDECAR_PORT}`;
const SIDECAR_CWD = resolve(HERE, "../sidecar");
const PYTHON =
  process.env.E2E_PYTHON ?? resolve(HERE, "../.venv/bin/python");

export default defineConfig({
  testDir: "./e2e",
  testMatch: /.*\.spec\.ts/,
  // Spawn the sidecar once per run.
  webServer: {
    command: `${PYTHON} -m attune_gui.main --port ${SIDECAR_PORT}`,
    cwd: SIDECAR_CWD,
    // `/healthz` requires a token param; the empty-state editor page
    // returns 200 without any auth and is a safe readiness probe.
    url: `${SIDECAR_URL}/editor`,
    timeout: 30_000,
    reuseExistingServer: !process.env.CI,
    env: {
      ATTUNE_CORPORA_REGISTRY: REGISTRY_PATH,
      ATTUNE_GUI_TEST: "1",
    },
    ignoreHTTPSErrors: false,
  },
  use: {
    baseURL: SIDECAR_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  // Run tests sequentially — they share the sidecar process and each
  // mutates the corpus on disk. Parallelism would race the registry.
  workers: 1,
  fullyParallel: false,
  reporter: process.env.CI ? "github" : "list",
  timeout: 30_000,
  expect: { timeout: 5_000 },
});
