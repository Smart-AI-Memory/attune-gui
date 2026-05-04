/**
 * Keyboard shortcuts + persistent advisory banner.
 *
 * Covers:
 *   - Cmd/Ctrl-S opens the save modal.
 *   - Cmd/Ctrl-K shows the "Command palette: coming in v2" toast.
 *   - Esc closes a top-level modal.
 *   - Generated-corpus advisory banner shows when `kind: "generated"`.
 *   - Save button is disabled while no diff exists; enabled after edit.
 *   - Diagnostics strip click jumps to the line in CodeMirror.
 */

import { test, expect } from "@playwright/test";

import { setupCorpus, openEditor, clearRegistry, fetchClientToken } from "./helpers";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const SIDECAR_PORT = process.env.E2E_SIDECAR_PORT ?? "8773";
const SIDECAR_URL = `http://127.0.0.1:${SIDECAR_PORT}`;

test.describe("keyboard shortcuts + advisories", () => {
  test.beforeEach(() => clearRegistry());

  test("Cmd/Ctrl-S opens the save modal when the doc is dirty", async ({ page, browserName }) => {
    const fx = await setupCorpus("kb-save", [
      {
        path: "x.md",
        frontmatter: { type: "concept", name: "X" },
        body: "body",
      },
    ]);
    try {
      await openEditor(page, fx.id, "x.md");
      await page.evaluate(() => {
        const view = (window as unknown as {
          __attuneEditor: { editor: { view: { state: { doc: { length: number } }; dispatch: (s: unknown) => void } } };
        }).__attuneEditor.editor.view;
        view.dispatch({ changes: { from: view.state.doc.length, insert: "\nMORE" } });
      });
      // The window-level keydown listener fires on dispatch from the
      // page context. `page.keyboard.press("Control+S")` is captured
      // by Chromium's native "Save Page" handler before bubbling, so
      // dispatch a synthetic KeyboardEvent on `window` instead.
      await page.evaluate((ctrlKey) => {
        window.dispatchEvent(new KeyboardEvent("keydown", {
          key: "s",
          [ctrlKey]: true,
          bubbles: true,
          cancelable: true,
        }));
      }, browserName === "webkit" ? "metaKey" : "ctrlKey");
      const modal = page.locator(".attune-modal").first();
      await expect(modal).toBeVisible();
    } finally {
      fx.cleanup();
    }
  });

  test("Cmd/Ctrl-K surfaces the v2 command-palette toast", async ({ page, browserName }) => {
    const fx = await setupCorpus("kb-palette", [
      {
        path: "x.md",
        frontmatter: { type: "concept", name: "X" },
        body: "body",
      },
    ]);
    try {
      await openEditor(page, fx.id, "x.md");
      await page.evaluate((ctrlKey) => {
        window.dispatchEvent(new KeyboardEvent("keydown", {
          key: "k",
          [ctrlKey]: true,
          bubbles: true,
          cancelable: true,
        }));
      }, browserName === "webkit" ? "metaKey" : "ctrlKey");
      const toast = page.locator(".attune-toast-show");
      await expect(toast).toBeVisible();
      await expect(toast).toContainText(/Command palette: coming in v2/);
    } finally {
      fx.cleanup();
    }
  });

  test("Esc closes the save modal", async ({ page }) => {
    const fx = await setupCorpus("kb-esc", [
      {
        path: "x.md",
        frontmatter: { type: "concept", name: "X" },
        body: "body",
      },
    ]);
    try {
      await openEditor(page, fx.id, "x.md");
      await page.evaluate(() => {
        const view = (window as unknown as {
          __attuneEditor: { editor: { view: { state: { doc: { length: number } }; dispatch: (s: unknown) => void } } };
        }).__attuneEditor.editor.view;
        view.dispatch({ changes: { from: view.state.doc.length, insert: "\nMORE" } });
      });
      await page.locator(".attune-editor-topbar-right .attune-btn-primary").click();
      const modal = page.locator(".attune-modal").first();
      await expect(modal).toBeVisible();
      // Escape is wired via `document.addEventListener('keydown', …)`
      // in the modal — dispatch on document for parity with how
      // Chromium delivers the event after `keyboard.press`.
      await page.evaluate(() => {
        document.dispatchEvent(new KeyboardEvent("keydown", {
          key: "Escape",
          bubbles: true,
          cancelable: true,
        }));
      });
      await expect(modal).toHaveCount(0);
    } finally {
      fx.cleanup();
    }
  });

  test("generated-corpus advisory shows when kind === 'generated'", async ({ page, request }) => {
    // Register a corpus directly via the API with kind=generated.
    const token = await fetchClientToken();
    const root = mkdtempSync(join(tmpdir(), "attune-e2e-gen-"));
    mkdirSync(resolve(root, "concepts"), { recursive: true });
    writeFileSync(
      resolve(root, "concepts/foo.md"),
      `---\ntype: concept\nname: Foo\n---\nbody\n`,
      "utf-8",
    );
    try {
      await request.post(`${SIDECAR_URL}/api/corpus/register`, {
        headers: { "X-Attune-Client": token, "Content-Type": "application/json" },
        data: { name: "gen-test", path: root, kind: "generated" },
      });
      await openEditor(page, "gen-test", "concepts/foo.md");
      const advisory = page.locator(".attune-advisory-generated");
      await expect(advisory).toBeVisible();
      await expect(advisory).toContainText(/regenerated/);
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("Save button is disabled when doc matches base; enables after first edit", async ({ page }) => {
    const fx = await setupCorpus("save-button", [
      {
        path: "x.md",
        frontmatter: { type: "concept", name: "X" },
        body: "body",
      },
    ]);
    try {
      await openEditor(page, fx.id, "x.md");
      const saveBtn = page.locator(".attune-editor-topbar-right .attune-btn-primary");
      await expect(saveBtn).toBeDisabled();
      await page.evaluate(() => {
        const view = (window as unknown as {
          __attuneEditor: { editor: { view: { state: { doc: { length: number } }; dispatch: (s: unknown) => void } } };
        }).__attuneEditor.editor.view;
        view.dispatch({ changes: { from: view.state.doc.length, insert: "\nMORE" } });
      });
      await expect(saveBtn).toBeEnabled();
    } finally {
      fx.cleanup();
    }
  });

  test("diagnostics strip click jumps the editor to that line", async ({ page }) => {
    const fx = await setupCorpus("diag-jump", [
      {
        path: "x.md",
        frontmatter: { type: "concept", name: "X" },
        // Body has a broken alias on line ~5 (after frontmatter): `[[nonexistent]]`.
        body: "line one\nline two\nline three\n[[nonexistent-alias]]\n",
      },
    ]);
    try {
      await openEditor(page, fx.id, "x.md");
      // Wait for the linter to run.
      await page.waitForTimeout(500);
      const diag = page.locator(".attune-diag").first();
      await expect(diag).toBeVisible({ timeout: 4_000 });
      // Click the entry.
      await diag.click();
      // CodeMirror's selection moved to that line.
      const cmAnchor = await page.evaluate(() => {
        const view = (window as unknown as {
          __attuneEditor: { editor: { view: { state: { selection: { main: { head: number; anchor: number } }; doc: { lineAt: (n: number) => { number: number } } } } } };
        }).__attuneEditor.editor.view;
        const { head } = view.state.selection.main;
        return view.state.doc.lineAt(head).number;
      });
      expect(cmAnchor).toBeGreaterThan(1);
    } finally {
      fx.cleanup();
    }
  });
});
