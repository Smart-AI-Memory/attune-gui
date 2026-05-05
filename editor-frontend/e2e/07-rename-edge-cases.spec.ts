/**
 * Rename refactor — edge cases beyond the happy path.
 *
 * Covers:
 *   - Alias collision: renaming to a name another template owns
 *     surfaces a 409 banner with the owning_path; Apply stays disabled.
 *   - No-op preview: renaming to the same name shows the "same name"
 *     summary; Apply stays disabled.
 *   - Cancel button closes the modal without rewriting any file.
 *   - Empty plan (no references): summary says "no-op"; Apply disabled.
 */

import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { setupCorpus, openEditor, clearRegistry } from "./helpers";

test.describe("rename refactor: edge cases", () => {
  test.beforeEach(() => clearRegistry());

  test("alias collision surfaces the owning_path in a banner; Apply stays disabled", async ({ page }) => {
    const fx = await setupCorpus("rename-collision", [
      {
        path: "concepts/foo.md",
        frontmatter: { type: "concept", name: "Foo", aliases: ["alpha"] },
        body: "body",
      },
      {
        path: "concepts/bar.md",
        frontmatter: { type: "concept", name: "Bar", aliases: ["beta"] },
        body: "body",
      },
    ]);
    try {
      await openEditor(page, fx.id, "concepts/foo.md");
      // Rename `alpha` → `beta` (already declared by bar.md).
      await page.evaluate(() => {
        const handle = (window as unknown as {
          __attuneEditor: { openRename: (field: string, name: string) => void };
        }).__attuneEditor;
        handle.openRename("aliases", "alpha");
      });
      const modal = page.locator(".attune-modal-rename");
      const toInput = modal.locator(".attune-rename-inputs input").nth(1);
      await toInput.fill("beta");
      const banner = modal.locator(".attune-modal-lint");
      await expect(banner).toBeVisible({ timeout: 4_000 });
      await expect(banner).toContainText(/collision/i);
      await expect(banner).toContainText(/concepts\/bar\.md/);
      const apply = modal.locator(".attune-modal-foot .attune-btn-primary");
      await expect(apply).toBeDisabled();
    } finally {
      fx.cleanup();
    }
  });

  test("renaming to the same name shows the no-op message and disables Apply", async ({ page }) => {
    const fx = await setupCorpus("rename-noop", [
      {
        path: "concepts/foo.md",
        frontmatter: { type: "concept", name: "Foo", tags: ["alpha"] },
        body: "body",
      },
    ]);
    try {
      await openEditor(page, fx.id, "concepts/foo.md");
      await page.evaluate(() => {
        (window as unknown as {
          __attuneEditor: { openRename: (field: string, name: string) => void };
        }).__attuneEditor.openRename("tags", "alpha");
      });
      const modal = page.locator(".attune-modal-rename");
      const toInput = modal.locator(".attune-rename-inputs input").nth(1);
      await toInput.fill("alpha"); // same as old
      // No preview request fires; summary says "same as the old name".
      await expect(modal.locator(".attune-rename-summary")).toContainText(/same as the old name/, { timeout: 1_000 });
      const apply = modal.locator(".attune-modal-foot .attune-btn-primary");
      await expect(apply).toBeDisabled();
    } finally {
      fx.cleanup();
    }
  });

  test("Cancel closes the modal and writes nothing", async ({ page }) => {
    const fx = await setupCorpus("rename-cancel", [
      {
        path: "concepts/foo.md",
        frontmatter: { type: "concept", name: "Foo", tags: ["alpha"] },
        body: "body",
      },
    ]);
    try {
      const before = readFileSync(resolve(fx.root, "concepts/foo.md"), "utf-8");
      await openEditor(page, fx.id, "concepts/foo.md");
      await page.evaluate(() => {
        (window as unknown as {
          __attuneEditor: { openRename: (field: string, name: string) => void };
        }).__attuneEditor.openRename("tags", "alpha");
      });
      const modal = page.locator(".attune-modal-rename");
      const toInput = modal.locator(".attune-rename-inputs input").nth(1);
      await toInput.fill("alpha-renamed");
      // Don't apply — click Cancel.
      const cancel = modal.locator(".attune-modal-foot .attune-btn-secondary");
      await cancel.click();
      await expect(modal).toHaveCount(0);
      const after = readFileSync(resolve(fx.root, "concepts/foo.md"), "utf-8");
      expect(after).toBe(before);
    } finally {
      fx.cleanup();
    }
  });

  test("renaming a name that has zero references surfaces a no-op plan", async ({ page }) => {
    const fx = await setupCorpus("rename-empty-plan", [
      {
        path: "concepts/foo.md",
        frontmatter: { type: "concept", name: "Foo", tags: ["alpha"] },
        body: "body",
      },
    ]);
    try {
      await openEditor(page, fx.id, "concepts/foo.md");
      // Use a name that's NOT in the corpus — server returns an empty
      // edits list (a deliberate no-op plan, not an error).
      await page.evaluate(() => {
        (window as unknown as {
          __attuneEditor: { openRename: (field: string, name: string) => void };
        }).__attuneEditor.openRename("tags", "nonexistent-tag");
      });
      const modal = page.locator(".attune-modal-rename");
      const toInput = modal.locator(".attune-rename-inputs input").nth(1);
      await toInput.fill("anything-else");
      await expect(modal.locator(".attune-rename-summary")).toContainText(/no-op/, { timeout: 4_000 });
      const apply = modal.locator(".attune-modal-foot .attune-btn-primary");
      await expect(apply).toBeDisabled();
    } finally {
      fx.cleanup();
    }
  });
});
