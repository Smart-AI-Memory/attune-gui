/**
 * Corpus switcher — search threshold, add-corpus modal, read-only hash.
 *
 * Covers:
 *   - Search input only appears once registered count > 10.
 *   - Search filters items live as the user types.
 *   - Add-corpus modal: Cancel closes; valid name+path POSTs to
 *     /register and the new corpus appears in the dropdown.
 *   - Hash field: rendered with `readOnly: true`, can't be edited.
 */

import { test, expect } from "@playwright/test";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

import { setupCorpus, openEditor, clearRegistry, fetchClientToken } from "./helpers";

const SIDECAR_PORT = process.env.E2E_SIDECAR_PORT ?? "8773";
const SIDECAR_URL = `http://127.0.0.1:${SIDECAR_PORT}`;

test.describe("corpus switcher: extras", () => {
  test.beforeEach(() => clearRegistry());

  test("search input materializes above SEARCH_THRESHOLD (>10) and filters live", async ({ page, request }) => {
    // Register 12 throwaway corpora so the dropdown crosses the threshold.
    const token = await fetchClientToken();
    const tmp = mkdtempSync(join(tmpdir(), "attune-e2e-many-"));
    let firstCorpusId = "";
    try {
      for (let i = 0; i < 12; i++) {
        const root = resolve(tmp, `c${i}`);
        mkdirSync(root, { recursive: true });
        writeFileSync(
          resolve(root, "x.md"),
          `---\ntype: concept\nname: ${i === 7 ? "needle-target" : `Corpus ${i}`}\n---\nbody\n`,
          "utf-8",
        );
        const res = await request.post(`${SIDECAR_URL}/api/corpus/register`, {
          headers: { "X-Attune-Client": token, "Content-Type": "application/json" },
          data: {
            name: i === 7 ? "needle-corpus" : `Corpus ${i}`,
            path: root,
            kind: "ad-hoc",
          },
        });
        const entry = (await res.json()) as { id: string };
        if (i === 0) firstCorpusId = entry.id;
      }
      // Open the editor on the first registered corpus.
      await openEditor(page, firstCorpusId, "x.md");
      const trigger = page.locator(".attune-corpus-switcher");
      await trigger.click();
      const panel = page.locator(".attune-corpus-panel");
      await expect(panel).toBeVisible();
      const search = panel.locator(".attune-corpus-search");
      await expect(search).toBeVisible();
      // Filter by typing.
      await search.fill("needle");
      const items = panel.locator(".attune-corpus-item");
      await expect(items).toHaveCount(1);
      await expect(items.first()).toContainText("needle-corpus");
    } finally {
      rmSync(tmp, { recursive: true, force: true });
    }
  });

  test("Add corpus: cancel closes; submit registers + appears in the list", async ({ page }) => {
    const fx = await setupCorpus("switcher-add", [
      {
        path: "x.md",
        frontmatter: { type: "concept", name: "X" },
        body: "body",
      },
    ]);
    const newRoot = mkdtempSync(join(tmpdir(), "attune-e2e-newcorpus-"));
    mkdirSync(resolve(newRoot), { recursive: true });
    writeFileSync(
      resolve(newRoot, "a.md"),
      `---\ntype: concept\nname: A\n---\nfresh\n`,
      "utf-8",
    );
    try {
      await openEditor(page, fx.id, "x.md");
      await page.locator(".attune-corpus-switcher").click();
      // Cancel path first.
      await page.locator(".attune-corpus-add").click();
      const cancelModal = page.locator(".attune-modal-register");
      await expect(cancelModal).toBeVisible();
      await cancelModal.locator(".attune-modal-foot .attune-btn-secondary").click();
      await expect(cancelModal).toHaveCount(0);

      // Now actually register.
      await page.locator(".attune-corpus-switcher").click();
      await page.locator(".attune-corpus-add").click();
      const modal = page.locator(".attune-modal-register");
      await expect(modal).toBeVisible();
      const inputs = modal.locator(".attune-fm-input");
      await inputs.nth(0).fill("e2e-added-corpus");
      await inputs.nth(1).fill(newRoot);
      const add = modal.locator(".attune-modal-foot .attune-btn-primary");
      await expect(add).toBeEnabled();
      await add.click();
      await expect(modal).toHaveCount(0);

      // The new corpus shows in the dropdown next time it's opened.
      await page.locator(".attune-corpus-switcher").click();
      const items = page.locator(".attune-corpus-panel .attune-corpus-item");
      await expect(items.filter({ hasText: "e2e-added-corpus" })).toHaveCount(1);
    } finally {
      fx.cleanup();
      rmSync(newRoot, { recursive: true, force: true });
    }
  });

  test("readOnly hash field: input has readOnly attribute, typing has no effect", async ({ page }) => {
    const fx = await setupCorpus("readonly-hash", [
      {
        path: "x.md",
        frontmatter: { type: "concept", name: "X", hash: "sha256:abc123" },
        body: "body",
      },
    ]);
    try {
      await openEditor(page, fx.id, "x.md");
      const hashInput = page.locator("#attune-fm-hash");
      await expect(hashInput).toBeVisible();
      await expect(hashInput).toHaveValue("sha256:abc123");
      await expect(hashInput).toHaveAttribute("readonly", "");
      // Try to type — readOnly inputs swallow user input.
      await hashInput.click();
      await page.keyboard.type("xxx");
      await expect(hashInput).toHaveValue("sha256:abc123");
      // The row got the readonly modifier class.
      const row = page.locator(".attune-fm-row-readonly").filter({ has: hashInput });
      await expect(row).toHaveCount(1);
    } finally {
      fx.cleanup();
    }
  });
});
