/**
 * Conflict mode — every choice and every entry button.
 *
 * Covers:
 *   - "Reload from disk" replaces editor text with disk text, drops
 *     local edits, hides the banner.
 *   - "Keep local" hides the banner without reloading; subsequent
 *     save no longer 409s (base hash rebased to disk).
 *   - "Resolve" with "Use disk" keeps the disk-side text only.
 *   - "Resolve" with "Use editor" keeps the editor-side text only.
 *   - "Resolve" Cancel keeps the banner open (lets user pick again).
 *
 * (Keep-both is covered in 02-conflict-resolve.spec.ts.)
 */

import { test, expect } from "@playwright/test";
import { writeFileSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { setupCorpus, openEditor, readDoc, clearRegistry } from "./helpers";

async function setupConflict(page: import("@playwright/test").Page, label: string) {
  const fx = await setupCorpus(`conflict-${label}`, [
    {
      path: "x.md",
      frontmatter: { type: "concept", name: "X" },
      body: "shared line\n",
    },
  ]);
  await openEditor(page, fx.id, "x.md");
  // Local edit: replace "shared line" with "EDITOR".
  await page.evaluate(() => {
    const view = (window as unknown as {
      __attuneEditor: { editor: { view: { state: { doc: { toString(): string } }; dispatch: (s: unknown) => void } } };
    }).__attuneEditor.editor.view;
    const t = view.state.doc.toString();
    const i = t.indexOf("shared line");
    view.dispatch({ changes: { from: i, to: i + "shared line".length, insert: "EDITOR" } });
  });
  // Disk edit: replace "shared line" with "DISK".
  const onDisk = resolve(fx.root, "x.md");
  writeFileSync(onDisk, readFileSync(onDisk, "utf-8").replace("shared line", "DISK"));
  // Wait for the WS-pushed banner.
  await expect(page.locator(".attune-banner-conflict").first()).toBeVisible({ timeout: 8_000 });
  return fx;
}

test.describe("conflict mode: every entry + every choice", () => {
  test.beforeEach(() => clearRegistry());

  test("Reload from disk replaces editor with disk text", async ({ page }) => {
    const fx = await setupConflict(page, "reload");
    try {
      const banner = page.locator(".attune-banner-conflict").first();
      await banner.locator(".attune-btn-secondary").filter({ hasText: "Reload from disk" }).click();
      await expect(page.locator(".attune-editor-status")).toContainText(/reloaded · /);
      const text = await readDoc(page);
      expect(text).toContain("DISK");
      expect(text).not.toContain("EDITOR");
    } finally {
      fx.cleanup();
    }
  });

  test("Keep local preserves the editor text and rebases the hash", async ({ page }) => {
    const fx = await setupConflict(page, "keep");
    try {
      const banner = page.locator(".attune-banner-conflict").first();
      await banner.locator(".attune-btn-secondary").filter({ hasText: "Keep local" }).click();
      await expect(page.locator(".attune-editor-status")).toContainText(/kept local · /);
      const text = await readDoc(page);
      expect(text).toContain("EDITOR");
      expect(text).not.toContain("DISK");
      // Banner is gone.
      await expect(page.locator(".attune-banner-conflict")).toHaveCount(0);
    } finally {
      fx.cleanup();
    }
  });

  test("Resolve → Use disk produces only the disk side", async ({ page }) => {
    const fx = await setupConflict(page, "use-disk");
    try {
      const banner = page.locator(".attune-banner-conflict").first();
      await banner.locator(".attune-btn-primary").click();
      const modal = page.locator(".attune-modal-conflict");
      await expect(modal).toBeVisible();
      const conflict = modal.locator(".attune-conflict-region").first();
      await conflict.locator('input[type=radio][value=disk]').check();
      await modal.locator(".attune-modal-foot .attune-btn-primary").click();
      await expect(modal).toHaveCount(0);
      const text = await readDoc(page);
      expect(text).toContain("DISK");
      expect(text).not.toContain("EDITOR");
    } finally {
      fx.cleanup();
    }
  });

  test("Resolve → Use editor keeps only the editor side", async ({ page }) => {
    const fx = await setupConflict(page, "use-editor");
    try {
      const banner = page.locator(".attune-banner-conflict").first();
      await banner.locator(".attune-btn-primary").click();
      const modal = page.locator(".attune-modal-conflict");
      await expect(modal).toBeVisible();
      await modal.locator(".attune-conflict-region").first()
        .locator('input[type=radio][value=editor]').check();
      await modal.locator(".attune-modal-foot .attune-btn-primary").click();
      await expect(modal).toHaveCount(0);
      const text = await readDoc(page);
      expect(text).toContain("EDITOR");
      expect(text).not.toContain("DISK");
    } finally {
      fx.cleanup();
    }
  });

  test("Resolve modal Cancel reopens the banner choice", async ({ page }) => {
    const fx = await setupConflict(page, "cancel");
    try {
      const banner = page.locator(".attune-banner-conflict").first();
      await banner.locator(".attune-btn-primary").click();
      const modal = page.locator(".attune-modal-conflict");
      await expect(modal).toBeVisible();
      await modal.locator(".attune-modal-foot .attune-btn-secondary").click();
      await expect(modal).toHaveCount(0);
      // Banner stays — user can re-click Resolve.
      await expect(banner).toBeVisible();
    } finally {
      fx.cleanup();
    }
  });

  test("Done is disabled until every conflict has a choice", async ({ page }) => {
    const fx = await setupConflict(page, "done-gate");
    try {
      const banner = page.locator(".attune-banner-conflict").first();
      await banner.locator(".attune-btn-primary").click();
      const modal = page.locator(".attune-modal-conflict");
      const done = modal.locator(".attune-modal-foot .attune-btn-primary");
      await expect(done).toBeDisabled();
      await expect(modal.locator(".attune-modal-status")).toContainText(/0 of 1/);
      await modal.locator('input[type=radio][value=both]').first().check();
      await expect(modal.locator(".attune-modal-status")).toContainText(/1 of 1/);
      await expect(done).toBeEnabled();
    } finally {
      fx.cleanup();
    }
  });
});
