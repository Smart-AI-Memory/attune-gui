/**
 * Golden flow #1: open → edit → save.
 *
 * Loads a real template, makes a textual edit through the
 * CodeMirror view, opens the per-hunk save modal, accepts all
 * hunks, and verifies the saved text on disk.
 */

import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { setupCorpus, openEditor, clearRegistry } from "./helpers";

test.describe("flow: open → edit → save", () => {
  test.beforeEach(() => clearRegistry());


  test("typing in the editor + Save N of M roundtrips to disk", async ({ page }) => {
    const fx = await setupCorpus("flow-save", [
      {
        path: "concepts/intro.md",
        frontmatter: { type: "concept", name: "Intro" },
        body: "First paragraph.\n\nSecond paragraph.",
      },
    ]);
    try {
      await openEditor(page, fx.id, "concepts/intro.md");

      // Editor is loaded — Save button is disabled until we type.
      const saveBtn = page.locator(".attune-editor-topbar-right .attune-btn-primary");
      await expect(saveBtn).toBeDisabled();

      // Append a line through CodeMirror's `dispatch`.
      await page.evaluate(() => {
        const handle = (window as unknown as {
          __attuneEditor: { editor: { view: { state: { doc: { length: number } }; dispatch: (s: unknown) => void } } };
        }).__attuneEditor;
        const view = handle.editor.view;
        view.dispatch({
          changes: { from: view.state.doc.length, insert: "\n\nThird paragraph." },
        });
      });

      await expect(saveBtn).toBeEnabled();
      await saveBtn.click();

      const modal = page.locator(".attune-modal");
      await expect(modal).toBeVisible();
      // At least one hunk shows up.
      await expect(modal.locator(".attune-hunk").first()).toBeVisible();
      // Default-checked: button label says "Save 1 hunk" (or "all 1").
      const submit = modal.locator(".attune-modal-foot .attune-btn-primary");
      await expect(submit).toBeEnabled();

      // Wait for any in-flight projected lint to settle, then click.
      await page.waitForTimeout(300);
      await submit.click();

      // Modal closes, status switches to "saved · …".
      await expect(modal).toHaveCount(0);
      await expect(page.locator(".attune-editor-status")).toHaveText(/saved · /);

      // The file on disk now contains the appended paragraph.
      const onDisk = readFileSync(resolve(fx.root, "concepts/intro.md"), "utf-8");
      expect(onDisk).toContain("Third paragraph.");
    } finally {
      fx.cleanup();
    }
  });
});
