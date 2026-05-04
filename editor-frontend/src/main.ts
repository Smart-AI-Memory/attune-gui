/**
 * Template editor entry point.
 *
 * Bootstraps the layout (top bar, frontmatter sidebar, editor pane,
 * diagnostics strip), reads the corpus + path bootstrap data from the
 * Jinja shell, fetches the template via the API, and mounts CodeMirror
 * with the linter + autocomplete extensions.
 */

import "./style.css";
import { EditorView } from "@codemirror/view";
import { EditorApi, ApiError } from "./api";
import { TemplateDocument } from "./document-model";
import { mountEditor, type MountedEditor } from "./editor";
import { renderFrontmatterForm } from "./frontmatter-form";
import { attuneLinter } from "./lint";
import { renderDiagnosticsStrip } from "./diagnostics-strip";
import { attuneCompletions } from "./autocomplete";
import { openSaveModal } from "./save-modal";

interface Bootstrap {
  corpusId: string;
  relPath: string;
  sessionToken: string;
}

const ROOT_ID = "attune-editor-root";

function readBootstrap(root: HTMLElement): Bootstrap {
  return {
    corpusId: root.dataset.corpusId ?? "",
    relPath: root.dataset.relPath ?? "",
    sessionToken: root.dataset.sessionToken ?? "",
  };
}

interface Layout {
  status: HTMLElement;
  pathLabel: HTMLElement;
  banner: HTMLElement;
  formSidebar: HTMLElement;
  editorPane: HTMLElement;
  diagnostics: HTMLElement;
  saveBtn: HTMLButtonElement;
  toast: HTMLElement;
}

function buildLayout(root: HTMLElement): Layout {
  root.innerHTML = "";
  root.classList.add("attune-editor-shell");

  const topBar = document.createElement("header");
  topBar.className = "attune-editor-topbar";

  const pathLabel = document.createElement("span");
  pathLabel.className = "attune-editor-path";

  const right = document.createElement("div");
  right.className = "attune-editor-topbar-right";
  const status = document.createElement("span");
  status.className = "attune-editor-status";
  const saveBtn = document.createElement("button");
  saveBtn.type = "button";
  saveBtn.className = "attune-btn attune-btn-primary";
  saveBtn.textContent = "Save";
  saveBtn.disabled = true;
  saveBtn.title = "Save (⌘S)";
  right.appendChild(status);
  right.appendChild(saveBtn);

  topBar.appendChild(pathLabel);
  topBar.appendChild(right);

  const banner = document.createElement("div");
  banner.className = "attune-editor-banner";
  banner.hidden = true;

  const main = document.createElement("div");
  main.className = "attune-editor-main";

  const formSidebar = document.createElement("aside");
  formSidebar.className = "attune-editor-sidebar";

  const editorPane = document.createElement("section");
  editorPane.className = "attune-editor-pane";

  main.appendChild(formSidebar);
  main.appendChild(editorPane);

  const diagnostics = document.createElement("footer");
  diagnostics.className = "attune-editor-diagnostics";

  const toast = document.createElement("div");
  toast.className = "attune-toast";
  toast.setAttribute("role", "status");
  toast.setAttribute("aria-live", "polite");

  root.appendChild(topBar);
  root.appendChild(banner);
  root.appendChild(main);
  root.appendChild(diagnostics);
  root.appendChild(toast);

  return { status, pathLabel, banner, formSidebar, editorPane, diagnostics, saveBtn, toast };
}

function showToast(toast: HTMLElement, msg: string, kind: "ok" | "err" = "ok"): void {
  toast.textContent = msg;
  toast.className = `attune-toast attune-toast-${kind} attune-toast-show`;
  setTimeout(() => {
    toast.className = "attune-toast";
  }, 3200);
}

async function bootstrap(): Promise<void> {
  const root = document.getElementById(ROOT_ID);
  if (!root) return;

  const boot = readBootstrap(root);
  const ui = buildLayout(root);

  ui.pathLabel.textContent = boot.relPath
    ? `${boot.corpusId} · ${boot.relPath}`
    : "no template loaded";

  if (!boot.corpusId || !boot.relPath) {
    ui.status.textContent = "Open a template via `attune edit <path>` to begin.";
    return;
  }

  ui.status.textContent = "Loading…";
  const api = new EditorApi(boot.sessionToken);

  let template;
  try {
    template = await api.loadTemplate(boot.corpusId, boot.relPath);
  } catch (err) {
    ui.status.textContent =
      err instanceof ApiError
        ? `Load failed (${err.status}): ${err.message}`
        : "Load failed.";
    return;
  }

  const doc = new TemplateDocument(template.text);

  let editor: MountedEditor | null = null;
  let strip: ReturnType<typeof renderDiagnosticsStrip> | null = null;
  // Re-entrancy guards: avoid feedback loops when one view drives the other.
  let suppressEditorChange = false;
  let suppressFormRefresh = false;

  // Save-flow state — kept in scope so onChange can read it.
  let baseText = template.text;
  let baseHash = template.base_hash;
  function refreshSaveButton(): void {
    if (!editor) return;
    const draft = editor.view.state.doc.toString();
    ui.saveBtn.disabled = draft === baseText;
  }

  const form = renderFrontmatterForm(ui.formSidebar, {
    doc,
    onChange: () => {
      if (suppressFormRefresh) return;
      const newText = doc.getText();
      if (editor && editor.view.state.doc.toString() !== newText) {
        suppressEditorChange = true;
        editor.setText(newText);
        suppressEditorChange = false;
      }
    },
  });

  const completions = attuneCompletions({ api, corpusId: boot.corpusId });
  const linter = attuneLinter({
    api,
    corpusId: boot.corpusId,
    relPath: boot.relPath,
    onDiagnostics: (diags) => strip?.setDiagnostics(diags),
  });

  // Update listener for save-button enabled state — fires on every
  // doc change (typed or programmatic).
  const saveButtonRefresh = EditorView.updateListener.of((u) => {
    if (u.docChanged) refreshSaveButton();
  });

  editor = mountEditor({
    parent: ui.editorPane,
    initialText: template.text,
    baseText: template.text,
    extra: [linter, completions.extension, saveButtonRefresh],
    onChange: (text) => {
      if (suppressEditorChange) return;
      doc.setText(text);
      suppressFormRefresh = true;
      form.refresh();
      suppressFormRefresh = false;
    },
  });

  strip = renderDiagnosticsStrip(ui.diagnostics, { view: editor.view });
  ui.status.textContent = `loaded · base ${template.base_hash}`;
  refreshSaveButton();

  function showConflictBanner(): void {
    ui.banner.hidden = false;
    ui.banner.className = "attune-editor-banner attune-banner-conflict";
    ui.banner.innerHTML = "";
    const msg = document.createElement("span");
    msg.textContent =
      "This file changed on disk. Reload to continue. (Three-way merge: M4 task #20.)";
    const reload = document.createElement("button");
    reload.type = "button";
    reload.className = "attune-btn attune-btn-secondary";
    reload.textContent = "Reload from disk";
    reload.addEventListener("click", () => {
      void reloadFromDisk();
    });
    ui.banner.appendChild(msg);
    ui.banner.appendChild(reload);
  }

  async function reloadFromDisk(): Promise<void> {
    try {
      const fresh = await api.loadTemplate(boot.corpusId, boot.relPath);
      baseText = fresh.text;
      baseHash = fresh.base_hash;
      doc.setText(fresh.text);
      suppressEditorChange = true;
      editor!.setText(fresh.text);
      editor!.setBase(fresh.text);
      suppressEditorChange = false;
      suppressFormRefresh = true;
      form.refresh();
      suppressFormRefresh = false;
      ui.banner.hidden = true;
      ui.status.textContent = `reloaded · base ${baseHash}`;
      refreshSaveButton();
    } catch (err) {
      showToast(ui.toast, `Reload failed: ${(err as Error).message}`, "err");
    }
  }

  async function openSave(): Promise<void> {
    const draft = editor!.view.state.doc.toString();
    if (draft === baseText) return; // nothing to save
    let diff;
    try {
      diff = await api.diffTemplate(boot.corpusId, {
        path: boot.relPath,
        draft_text: draft,
        base_hash: baseHash,
      });
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        showConflictBanner();
        return;
      }
      showToast(ui.toast, `Diff failed: ${(err as Error).message}`, "err");
      return;
    }

    if (diff.hunks.length === 0) {
      showToast(ui.toast, "No diff against base.");
      return;
    }

    openSaveModal({
      parent: document.body,
      baseText,
      hunks: diff.hunks,
      onLint: (projected) =>
        api.lint(boot.corpusId, { path: boot.relPath, text: projected }),
      onSave: async (acceptedIds) => {
        const result = await api.saveTemplate(boot.corpusId, {
          path: boot.relPath,
          draft_text: draft,
          base_hash: baseHash,
          accepted_hunks: acceptedIds,
        });
        // After save, the new on-disk text is what the server wrote —
        // re-fetch so the editor's base stays accurate (handles
        // partial-hunk saves where the on-disk text differs from the
        // current draft).
        const fresh = await api.loadTemplate(boot.corpusId, boot.relPath);
        baseText = fresh.text;
        baseHash = fresh.base_hash;
        editor!.setBase(fresh.text);
        // If the user saved fewer than all hunks, the editor's draft
        // is still ahead of base — leave it alone so the user can
        // keep editing. If they saved everything, sync the editor to
        // match disk.
        if (acceptedIds.length === diff.hunks.length) {
          suppressEditorChange = true;
          editor!.setText(fresh.text);
          suppressEditorChange = false;
          doc.setText(fresh.text);
          suppressFormRefresh = true;
          form.refresh();
          suppressFormRefresh = false;
        }
        ui.status.textContent = `saved · ${result.new_hash}`;
        showToast(ui.toast, `Saved (${acceptedIds.length} of ${diff.hunks.length} hunks).`);
        refreshSaveButton();
      },
      onConflict: showConflictBanner,
    });
  }

  ui.saveBtn.addEventListener("click", () => void openSave());

  // Cmd/Ctrl-S opens the save modal. Trap before the browser does.
  window.addEventListener("keydown", (ev) => {
    if ((ev.metaKey || ev.ctrlKey) && ev.key === "s") {
      ev.preventDefault();
      if (!ui.saveBtn.disabled) void openSave();
    }
  });

  window.addEventListener("beforeunload", (ev) => {
    if (editor && editor.view.state.doc.toString() !== baseText) {
      ev.preventDefault();
      ev.returnValue = "";
    }
  });

  // Expose a tiny debug handle for live verification (preview_eval).
  // Not used by production code paths.
  (window as unknown as { __attuneEditor?: unknown }).__attuneEditor = {
    api,
    doc,
    editor,
    invalidateCompletions: completions.invalidateCache,
    save: openSave,
    reload: reloadFromDisk,
  };
}

if (document.readyState === "loading") {
  document.addEventListener(
    "DOMContentLoaded",
    () => {
      void bootstrap();
    },
    { once: true },
  );
} else {
  void bootstrap();
}
