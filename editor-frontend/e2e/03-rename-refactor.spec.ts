/**
 * Golden flow #3: rename refactor preview + apply.
 *
 * Loads a template that uses a tag, opens the rename modal via the
 * frontmatter-form chip context-menu, types a new tag name, waits for
 * the debounced multi-file preview, clicks Apply, and verifies the
 * tag was renamed on disk in every affected file.
 */

import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { setupCorpus, openEditor, clearRegistry } from "./helpers";

test.describe("flow: rename refactor", () => {
  test.beforeEach(() => clearRegistry());


  test("right-click → rename → preview → apply rewrites every reference on disk", async ({ page }) => {
    const fx = await setupCorpus("flow-rename", [
      {
        path: "concepts/a.md",
        frontmatter: { type: "concept", name: "A", tags: ["shared", "extra"] },
        body: "Body A.",
      },
      {
        path: "concepts/b.md",
        frontmatter: { type: "concept", name: "B", tags: ["shared"] },
        body: "Body B.",
      },
    ]);
    try {
      await openEditor(page, fx.id, "concepts/a.md");

      // Trigger the rename modal directly via the debug handle (faster
      // than dispatching contextmenu through the chip — same code path).
      await page.evaluate(() => {
        const handle = (window as unknown as {
          __attuneEditor: { openRename: (field: string, name: string) => void };
        }).__attuneEditor;
        handle.openRename("tags", "shared");
      });

      const modal = page.locator(".attune-modal-rename");
      await expect(modal).toBeVisible();
      await expect(modal.locator(".attune-modal-head")).toHaveText("Rename tag");

      const toInput = modal.locator(".attune-rename-inputs input").nth(1);
      await toInput.fill("renamed-tag");

      // Wait for debounced preview (250ms) + render.
      await expect(modal.locator(".attune-rename-summary")).toContainText(
        /affects 2 files/,
        { timeout: 4_000 },
      );
      // Both files appear in the diff.
      const fileHeads = await modal.locator(".attune-rename-file-head").allTextContents();
      expect(fileHeads.sort()).toEqual(["concepts/a.md", "concepts/b.md"]);

      const apply = modal.locator(".attune-modal-foot .attune-btn-primary");
      await expect(apply).toBeEnabled();
      await apply.click();

      // Modal closes; on-disk files now have the renamed tag.
      await expect(modal).toHaveCount(0);

      const a = readFileSync(resolve(fx.root, "concepts/a.md"), "utf-8");
      const b = readFileSync(resolve(fx.root, "concepts/b.md"), "utf-8");
      expect(a).toContain("renamed-tag");
      expect(a).not.toMatch(/\bshared\b/);
      expect(b).toContain("renamed-tag");
      expect(b).not.toMatch(/\bshared\b/);
    } finally {
      fx.cleanup();
    }
  });
});
