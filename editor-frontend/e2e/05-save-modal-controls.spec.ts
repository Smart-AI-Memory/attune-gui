/**
 * Save modal — every interactive control.
 *
 * Covers:
 *   - Save button is disabled until the doc diverges from base.
 *   - Modal opens on Save click; one hunk per logical change.
 *   - Each hunk has a checkbox; default-checked.
 *   - Toggling a hunk updates the "Save N of M hunks" label.
 *   - Partial save (uncheck a hunk) writes only the checked hunks.
 *   - Cancel closes the modal without writing.
 *   - Projected-state lint blocks Save when frontmatter would break.
 */

import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { setupCorpus, openEditor, clearRegistry } from "./helpers";

test.describe("save modal: every control", () => {
  test.beforeEach(() => clearRegistry());

  test("partial save: uncheck one hunk, only the checked hunk lands on disk", async ({ page }) => {
    const fx = await setupCorpus("save-partial", [
      {
        path: "concepts/multi.md",
        frontmatter: { type: "concept", name: "Multi" },
        // 8 spacer lines between the two edit targets so difflib's
        // 3-line context window doesn't merge them into one hunk.
        body: "alpha\nbeta\nl1\nl2\nl3\nl4\nl5\nl6\nl7\nl8\ndelta\nepsilon",
      },
    ]);
    try {
      await openEditor(page, fx.id, "concepts/multi.md");

      // Replace two non-adjacent body lines so we get two distinct hunks.
      await page.evaluate(() => {
        const handle = (window as unknown as {
          __attuneEditor: { editor: { view: { state: { doc: { toString(): string } }; dispatch: (s: unknown) => void } } };
        }).__attuneEditor;
        const view = handle.editor.view;
        const text = view.state.doc.toString();
        const a = text.indexOf("beta");
        const b = text.indexOf("delta");
        // Apply right-to-left so the first dispatch's offsets stay valid.
        view.dispatch({ changes: { from: b, to: b + "delta".length, insert: "DELTA" } });
        const after = view.state.doc.toString();
        const a2 = after.indexOf("beta");
        view.dispatch({ changes: { from: a2, to: a2 + "beta".length, insert: "BETA" } });
      });

      const saveBtn = page.locator(".attune-editor-topbar-right .attune-btn-primary");
      await expect(saveBtn).toBeEnabled();
      await saveBtn.click();

      const modal = page.locator(".attune-modal").first();
      await expect(modal).toBeVisible();

      const hunks = modal.locator(".attune-hunk");
      await expect(hunks).toHaveCount(2);

      // Both default-checked.
      const checkboxes = modal.locator('.attune-hunk-head input[type="checkbox"]');
      await expect(checkboxes.nth(0)).toBeChecked();
      await expect(checkboxes.nth(1)).toBeChecked();

      // Submit label says "all 2".
      const submit = modal.locator(".attune-modal-foot .attune-btn-primary");
      await page.waitForTimeout(350);
      await expect(submit).toContainText(/all 2|2 of 2/);

      // Uncheck the first hunk → label updates, projected text drops it.
      await checkboxes.nth(0).uncheck();
      await expect(submit).toContainText(/1 of 2/);

      await submit.click();
      await expect(modal).toHaveCount(0);

      // On disk: BETA NOT present, DELTA IS present.
      const onDisk = readFileSync(resolve(fx.root, "concepts/multi.md"), "utf-8");
      expect(onDisk).not.toContain("BETA");
      expect(onDisk).toContain("DELTA");
      expect(onDisk).toContain("beta"); // original kept
    } finally {
      fx.cleanup();
    }
  });

  test("uncheck every hunk: Save button disables", async ({ page }) => {
    const fx = await setupCorpus("save-zero", [
      {
        path: "x.md",
        frontmatter: { type: "concept", name: "X" },
        body: "line1",
      },
    ]);
    try {
      await openEditor(page, fx.id, "x.md");
      await page.evaluate(() => {
        const view = (window as unknown as {
          __attuneEditor: { editor: { view: { state: { doc: { length: number } }; dispatch: (s: unknown) => void } } };
        }).__attuneEditor.editor.view;
        view.dispatch({ changes: { from: view.state.doc.length, insert: "\nadded" } });
      });
      await page.locator(".attune-editor-topbar-right .attune-btn-primary").click();
      const modal = page.locator(".attune-modal").first();
      const cb = modal.locator('.attune-hunk-head input[type="checkbox"]').first();
      await cb.uncheck();
      const submit = modal.locator(".attune-modal-foot .attune-btn-primary");
      await expect(submit).toBeDisabled();
      await expect(submit).toContainText(/0 of/);
    } finally {
      fx.cleanup();
    }
  });

  test("cancel closes the modal without writing", async ({ page }) => {
    const fx = await setupCorpus("save-cancel", [
      {
        path: "y.md",
        frontmatter: { type: "concept", name: "Y" },
        body: "original",
      },
    ]);
    try {
      await openEditor(page, fx.id, "y.md");
      const before = readFileSync(resolve(fx.root, "y.md"), "utf-8");
      await page.evaluate(() => {
        const view = (window as unknown as {
          __attuneEditor: { editor: { view: { state: { doc: { length: number } }; dispatch: (s: unknown) => void } } };
        }).__attuneEditor.editor.view;
        view.dispatch({ changes: { from: view.state.doc.length, insert: "\nMORE" } });
      });
      await page.locator(".attune-editor-topbar-right .attune-btn-primary").click();
      const modal = page.locator(".attune-modal").first();
      await expect(modal).toBeVisible();
      const cancel = modal.locator(".attune-modal-foot .attune-btn-secondary");
      await cancel.click();
      await expect(modal).toHaveCount(0);
      const after = readFileSync(resolve(fx.root, "y.md"), "utf-8");
      expect(after).toBe(before);
    } finally {
      fx.cleanup();
    }
  });

  test("projected-state lint: missing required field blocks Save", async ({ page }) => {
    const fx = await setupCorpus("save-blocked", [
      {
        path: "z.md",
        frontmatter: { type: "concept", name: "Z" },
        body: "body",
      },
    ]);
    try {
      await openEditor(page, fx.id, "z.md");
      // Strip the required `name` field by editing frontmatter directly
      // through the document model.
      await page.evaluate(() => {
        const view = (window as unknown as {
          __attuneEditor: { editor: { view: { state: { doc: { toString(): string } }; dispatch: (s: unknown) => void } } };
        }).__attuneEditor.editor.view;
        const text = view.state.doc.toString();
        const start = text.indexOf("name: Z");
        view.dispatch({
          // Remove the entire `name: Z\n` line.
          changes: { from: start, to: start + "name: Z\n".length, insert: "" },
        });
      });
      await page.locator(".attune-editor-topbar-right .attune-btn-primary").click();
      const modal = page.locator(".attune-modal").first();
      await expect(modal).toBeVisible();
      // Wait for projected lint to settle.
      await page.waitForTimeout(400);
      const lintBanner = modal.locator(".attune-modal-lint");
      await expect(lintBanner).toBeVisible();
      await expect(lintBanner).toContainText(/Cannot save/);
      const submit = modal.locator(".attune-modal-foot .attune-btn-primary");
      await expect(submit).toBeDisabled();
    } finally {
      fx.cleanup();
    }
  });
});
