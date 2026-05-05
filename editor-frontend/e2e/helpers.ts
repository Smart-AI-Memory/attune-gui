/**
 * Helpers shared by the four golden-flow specs.
 *
 * - `setupCorpus(name)` writes a fresh template corpus into a temp
 *   dir and registers it with the sidecar via `/api/corpus/register`.
 *   Each spec gets its own isolated corpus so they don't see each
 *   other's state.
 * - `openEditor(page, ...)` navigates to `/editor?corpus=…&path=…`
 *   and waits for the editor to mount.
 * - `clientToken(page)` reads the session token from the bootstrap
 *   data attribute so mutating routes can echo it on the
 *   `X-Attune-Client` header.
 */

import { mkdtempSync, mkdirSync, writeFileSync, rmSync, existsSync, unlinkSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { request as apiRequest } from "@playwright/test";
import type { Page, APIRequestContext } from "@playwright/test";

const HERE = dirname(fileURLToPath(import.meta.url));
const REGISTRY_PATH = resolve(HERE, ".tmp/corpora.json");

/**
 * Wipe the test-only corpora registry. Call in `beforeEach` so each
 * spec starts with an empty registry; previous specs' fixture-corpora
 * don't leak into this one's switcher dropdown.
 */
export function clearRegistry(): void {
  if (existsSync(REGISTRY_PATH)) {
    unlinkSync(REGISTRY_PATH);
  }
}

export interface TemplateSpec {
  /** Rel-path inside the corpus root, e.g. "concepts/foo.md". */
  path: string;
  /** Frontmatter dict — flatly serialized to YAML. */
  frontmatter: Record<string, string | string[]>;
  /** Body markdown (no frontmatter delimiters). */
  body: string;
}

export interface CorpusFixture {
  id: string;
  name: string;
  root: string;
  /** Tear down: delete the temp dir. */
  cleanup(): void;
}

const SIDECAR_PORT = process.env.E2E_SIDECAR_PORT ?? "8773";
const SIDECAR_URL = `http://127.0.0.1:${SIDECAR_PORT}`;

function yamlDump(fm: Record<string, string | string[]>): string {
  const lines: string[] = [];
  for (const [k, v] of Object.entries(fm)) {
    if (Array.isArray(v)) {
      lines.push(`${k}: [${v.map((s) => s).join(", ")}]`);
    } else {
      lines.push(`${k}: ${v}`);
    }
  }
  return lines.join("\n");
}

export function writeCorpus(root: string, templates: readonly TemplateSpec[]): void {
  for (const t of templates) {
    const full = resolve(root, t.path);
    mkdirSync(resolve(full, ".."), { recursive: true });
    const fm = yamlDump(t.frontmatter);
    writeFileSync(full, `---\n${fm}\n---\n${t.body}\n`, "utf-8");
  }
}

export async function fetchClientToken(): Promise<string> {
  const ctx = await apiRequest.newContext();
  const res = await ctx.get(`${SIDECAR_URL}/api/session/token`);
  if (!res.ok()) {
    throw new Error(`session/token returned ${res.status()}`);
  }
  const body = (await res.json()) as { token: string };
  await ctx.dispose();
  return body.token;
}

export async function registerCorpus(
  ctx: APIRequestContext,
  token: string,
  name: string,
  path: string,
): Promise<{ id: string }> {
  const res = await ctx.post(`${SIDECAR_URL}/api/corpus/register`, {
    headers: { "X-Attune-Client": token, "Content-Type": "application/json" },
    data: { name, path, kind: "ad-hoc" },
  });
  if (!res.ok()) {
    throw new Error(`register returned ${res.status()}: ${await res.text()}`);
  }
  return (await res.json()) as { id: string };
}

export async function setupCorpus(
  fixtureName: string,
  templates: readonly TemplateSpec[],
): Promise<CorpusFixture> {
  const root = mkdtempSync(join(tmpdir(), `attune-e2e-${fixtureName}-`));
  writeCorpus(root, templates);

  const token = await fetchClientToken();
  const ctx = await apiRequest.newContext();
  try {
    const entry = await registerCorpus(ctx, token, fixtureName, root);
    return {
      id: entry.id,
      name: fixtureName,
      root,
      cleanup() {
        rmSync(root, { recursive: true, force: true });
      },
    };
  } finally {
    await ctx.dispose();
  }
}

export async function openEditor(
  page: Page,
  corpusId: string,
  relPath: string,
): Promise<void> {
  await page.goto(`/editor?corpus=${corpusId}&path=${encodeURIComponent(relPath)}`);
  // The bundle bootstraps async; wait for either the loaded status or
  // the empty-state message.
  await page.waitForFunction(
    () => {
      const status = document.querySelector(".attune-editor-status");
      const text = status?.textContent ?? "";
      return /loaded · base|Open a template/.test(text);
    },
    { timeout: 10_000 },
  );
  // The WebSocket connects after bootstrap. Wait for `readyState() === 1`
  // (OPEN) so callers that mutate disk and expect a `file_changed`
  // push don't race the connection.
  await page.waitForFunction(
    () => {
      const handle = (window as unknown as {
        __attuneEditor?: { ws?: { readyState?: () => number } };
      }).__attuneEditor;
      return handle?.ws?.readyState?.() === 1;
    },
    { timeout: 5_000 },
  ).catch(() => {
    // Empty-state pages skip the WS — silence the timeout.
  });
}

export async function readDoc(page: Page): Promise<string> {
  return await page.evaluate(() => {
    const handle = (window as unknown as {
      __attuneEditor?: { editor: { view: { state: { doc: { toString(): string } } } } };
    }).__attuneEditor;
    return handle?.editor?.view?.state?.doc?.toString() ?? "";
  });
}
