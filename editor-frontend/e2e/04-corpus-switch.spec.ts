/**
 * Golden flow #4: corpus switcher + unsaved-edits guard.
 *
 * Sets up two corpora, opens the editor on the first, registers the
 * second via the API, types unsaved edits, opens the switcher
 * dropdown, picks the second corpus, and verifies:
 *
 *   - the unsaved-edits prompt appears with Save / Discard / Cancel
 *   - Cancel keeps the editor on the original corpus
 *   - Discard navigates to /editor (empty state) for the new active
 */

import { test, expect } from "@playwright/test";

import { setupCorpus, openEditor, clearRegistry } from "./helpers";

test.describe("flow: corpus switcher + unsaved-edits guard", () => {
  test.beforeEach(() => clearRegistry());


  test("dirty editor → switch → prompt → Cancel keeps state; Discard switches", async ({ page }) => {
    const fx1 = await setupCorpus("flow-switch-a", [
      {
        path: "concepts/intro.md",
        frontmatter: { type: "concept", name: "Intro" },
        body: "First corpus body.",
      },
    ]);
    const fx2 = await setupCorpus("flow-switch-b", [
      {
        path: "concepts/other.md",
        frontmatter: { type: "concept", name: "Other" },
        body: "Second corpus body.",
      },
    ]);
    try {
      await openEditor(page, fx1.id, "concepts/intro.md");

      // Dirty the editor.
      await page.evaluate(() => {
        const handle = (window as unknown as {
          __attuneEditor: { editor: { view: { state: { doc: { length: number } }; dispatch: (s: unknown) => void } } };
        }).__attuneEditor;
        const view = handle.editor.view;
        view.dispatch({
          changes: { from: view.state.doc.length, insert: "\nDIRTY EDIT\n" },
        });
      });

      // Open the switcher dropdown.
      const trigger = page.locator(".attune-corpus-switcher");
      await trigger.click();

      const dropdown = page.locator(".attune-corpus-panel");
      await expect(dropdown).toBeVisible();
      // Both corpora are listed — earlier specs can leak entries into
      // the shared sidecar registry, so don't assert exact count.
      const items = dropdown.locator(".attune-corpus-item");
      await expect(items.filter({ hasText: "flow-switch-a" })).toHaveCount(1);
      await expect(items.filter({ hasText: "flow-switch-b" })).toHaveCount(1);

      // Click the *second* corpus.
      const target = items.filter({ hasText: "flow-switch-b" });
      await target.click();

      // Unsaved-edits prompt appears.
      const prompt = page.locator(".attune-modal-unsaved");
      await expect(prompt).toBeVisible();
      const cancel = prompt.locator(".attune-btn-secondary").filter({ hasText: "Cancel" });
      await cancel.click();
      await expect(prompt).toHaveCount(0);

      // Editor is still on corpus 1, dirty edit preserved.
      const status = page.locator(".attune-editor-status");
      await expect(status).toContainText(/loaded · base/);
      const doc = await page.evaluate(() => {
        const handle = (window as unknown as {
          __attuneEditor: { editor: { view: { state: { doc: { toString(): string } } } } };
        }).__attuneEditor;
        return handle.editor.view.state.doc.toString();
      });
      expect(doc).toContain("DIRTY EDIT");

      // Reopen, click Discard this time.
      await trigger.click();
      await expect(dropdown).toBeVisible();
      await items.filter({ hasText: "flow-switch-b" }).click();

      const prompt2 = page.locator(".attune-modal-unsaved");
      await expect(prompt2).toBeVisible();
      await prompt2.locator(".attune-btn-secondary").filter({ hasText: "Discard" }).click();

      // Navigation kicks in — empty editor state appears for the new
      // active corpus.
      await page.waitForURL(/\/editor$/, { timeout: 5_000 });
      await expect(page.locator(".attune-editor-status")).toContainText(/Open a template/);
    } finally {
      fx1.cleanup();
      fx2.cleanup();
    }
  });
});
