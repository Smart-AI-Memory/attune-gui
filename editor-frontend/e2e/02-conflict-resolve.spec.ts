/**
 * Golden flow #2: external edit on disk → conflict mode → resolve.
 *
 * Loads a template, makes a local edit in the editor, then writes a
 * different change to the file on disk. The sidecar's WebSocket pushes
 * `file_changed`; the conflict banner appears; we click Resolve, pick
 * "Keep both", click Done, and verify the editor's text now contains
 * both edits and the status reflects a new base hash.
 */

import { test, expect } from "@playwright/test";
import { writeFileSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { setupCorpus, openEditor, readDoc, clearRegistry } from "./helpers";

test.describe("flow: external edit → conflict → resolve", () => {
  test.beforeEach(() => clearRegistry());


  test("WS-pushed file_changed surfaces the merge UI; Keep both produces the union", async ({ page }) => {
    const fx = await setupCorpus("flow-conflict", [
      {
        path: "concepts/intro.md",
        frontmatter: { type: "concept", name: "Intro" },
        body: "shared line\n",
      },
    ]);
    try {
      await openEditor(page, fx.id, "concepts/intro.md");

      // Local edit — replace "shared line" with "EDITOR LINE".
      await page.evaluate(() => {
        const handle = (window as unknown as {
          __attuneEditor: { editor: { view: { state: { doc: { toString(): string } }; dispatch: (s: unknown) => void } } };
        }).__attuneEditor;
        const view = handle.editor.view;
        const text = view.state.doc.toString();
        const i = text.indexOf("shared line");
        view.dispatch({
          changes: { from: i, to: i + "shared line".length, insert: "EDITOR LINE" },
        });
      });

      // External disk edit — replace the same line with a different string.
      // Replacing the *same* base region from both sides guarantees an
      // overlap that diff3Merge classifies as a conflict (vs the
      // simpler insert-at-different-positions case which can auto-merge).
      const onDisk = resolve(fx.root, "concepts/intro.md");
      const original = readFileSync(onDisk, "utf-8");
      writeFileSync(onDisk, original.replace("shared line", "DISK LINE"), "utf-8");

      // Wait for the WS push + banner.
      const banner = page.locator(".attune-banner-conflict").first();
      await expect(banner).toBeVisible({ timeout: 8_000 });
      await expect(banner).toContainText(/changed on disk/);

      // Click Resolve…
      const resolveBtn = banner.locator(".attune-btn-primary");
      await resolveBtn.click();

      const modal = page.locator(".attune-modal-conflict");
      await expect(modal).toBeVisible();
      const conflict = modal.locator(".attune-conflict-region").first();
      await expect(conflict).toBeVisible();

      // Pick "Keep both" for the (sole) conflict region.
      await conflict.locator('input[type=radio][value=both]').check();

      const done = modal.locator(".attune-modal-foot .attune-btn-primary");
      await expect(done).toBeEnabled();
      await done.click();

      await expect(modal).toHaveCount(0);
      await expect(page.locator(".attune-editor-status")).toHaveText(/merged · /);

      const finalText = await readDoc(page);
      expect(finalText).toContain("DISK LINE");
      expect(finalText).toContain("EDITOR LINE");
    } finally {
      fx.cleanup();
    }
  });
});
