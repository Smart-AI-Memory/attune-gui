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
import { openEditorWebSocket, type WsClient } from "./ws";
import { showConflict, type ConflictBanner } from "./conflict-mode";
import { openRenameModal } from "./rename-modal";
import type { RenamableField } from "./frontmatter-form";
import { mountCorpusSwitcher, promptUnsavedEdits } from "./corpus-switcher";
import {
  setAdvisories,
  type Advisory,
  GENERATED_CORPUS_MESSAGE,
  DUPLICATE_SESSION_MESSAGE,
} from "./advisory-banner";

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
  advisoryBanner: HTMLElement;
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

  const advisoryBanner = document.createElement("div");
  advisoryBanner.className = "attune-advisory-strip";
  advisoryBanner.setAttribute("role", "status");
  advisoryBanner.setAttribute("aria-live", "polite");
  advisoryBanner.hidden = true;

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
  root.appendChild(advisoryBanner);
  root.appendChild(banner);
  root.appendChild(main);
  root.appendChild(diagnostics);
  root.appendChild(toast);

  return {
    status,
    pathLabel,
    advisoryBanner,
    banner,
    formSidebar,
    editorPane,
    diagnostics,
    saveBtn,
    toast,
  };
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

  const api = new EditorApi(boot.sessionToken);

  // The corpus switcher owns the path-label element; it renders the
  // active corpus name + a dropdown to switch or register corpora.
  // Mount it in both the empty and the loaded state so users can act
  // on the workspace from either.
  const switcher = mountCorpusSwitcher({
    api,
    trigger: ui.pathLabel,
    panelParent: document.body,
    modalParent: document.body,
    initialCorpusId: boot.corpusId,
    initialPath: boot.relPath,
    onSwitchRequested: async () => {
      if (!editor) return true;
      const dirty =
        editor.view.state.doc.toString() !== baseText && !isDuplicateTab;
      if (!dirty) return true;
      const choice = await promptUnsavedEdits(document.body);
      if (choice === null) return false;
      if (choice === "save") {
        // Open the save modal; if user saves successfully, baseText
        // updates and the dirty check on next click would pass.
        await openSave();
        return false;
      }
      // discard: drop edits silently, allow switch.
      return true;
    },
    onSwitched: () => {
      // Navigating to /editor with no params lands on the empty state
      // for the new active corpus. The user picks a template via
      // `attune edit <path>` from there.
      window.location.assign("/editor");
    },
  });

  if (!boot.corpusId || !boot.relPath) {
    ui.status.textContent = "Open a template via `attune edit <path>` to begin.";
    return;
  }

  ui.status.textContent = "Loading…";

  let template;
  let schema;
  let corpusList;
  try {
    [template, schema, corpusList] = await Promise.all([
      api.loadTemplate(boot.corpusId, boot.relPath),
      api.loadSchema(),
      api.listCorpora(),
    ]);
  } catch (err) {
    ui.status.textContent =
      err instanceof ApiError
        ? `Load failed (${err.status}): ${err.message}`
        : "Load failed.";
    return;
  }

  const activeCorpus = corpusList.corpora.find((c) => c.id === boot.corpusId);

  const doc = new TemplateDocument(template.text);

  let editor: MountedEditor | null = null;
  let strip: ReturnType<typeof renderDiagnosticsStrip> | null = null;
  // Re-entrancy guards: avoid feedback loops when one view drives the other.
  let suppressEditorChange = false;
  let suppressFormRefresh = false;

  // Save-flow state — kept in scope so onChange can read it.
  let baseText = template.text;
  let baseHash = template.base_hash;
  let isDuplicateTab = false;
  let isGeneratedCorpus = false;
  function renderAdvisories(): void {
    const advisories: Advisory[] = [];
    if (isGeneratedCorpus) {
      advisories.push({ kind: "generated", message: GENERATED_CORPUS_MESSAGE });
    }
    if (isDuplicateTab) {
      advisories.push({ kind: "duplicate_session", message: DUPLICATE_SESSION_MESSAGE });
    }
    setAdvisories(ui.advisoryBanner, advisories);
  }
  function refreshSaveButton(): void {
    if (!editor) return;
    if (isDuplicateTab) {
      ui.saveBtn.disabled = true;
      return;
    }
    const draft = editor.view.state.doc.toString();
    ui.saveBtn.disabled = draft === baseText;
  }

  let activeRenameModal: { close(): void } | null = null;
  function openRename(field: RenamableField, name: string): void {
    if (activeRenameModal !== null) return;
    activeRenameModal = openRenameModal({
      api,
      corpusId: boot.corpusId,
      kind: field === "tags" ? "tag" : "alias",
      currentName: name,
      parent: document.body,
      onSuccess: (affected) => {
        // The server already broadcasts file_changed events to other
        // open editors; for *this* tab, refresh the editor in place
        // so the new name appears without waiting for a WS round-trip.
        void reloadFromDisk();
        const summary =
          affected.length === 0
            ? `Renamed (no files changed).`
            : `Renamed across ${affected.length} file${affected.length === 1 ? "" : "s"}: ${affected.slice(0, 4).join(", ")}${affected.length > 4 ? "…" : ""}`;
        showToast(ui.toast, summary);
      },
      onClose: () => {
        activeRenameModal = null;
      },
    });
  }

  const form = renderFrontmatterForm(ui.formSidebar, {
    doc,
    schema,
    onChange: () => {
      if (suppressFormRefresh) return;
      const newText = doc.getText();
      if (editor && editor.view.state.doc.toString() !== newText) {
        suppressEditorChange = true;
        editor.setText(newText);
        suppressEditorChange = false;
      }
    },
    onRename: openRename,
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
  if (activeCorpus?.kind === "generated") {
    isGeneratedCorpus = true;
  }
  renderAdvisories();
  refreshSaveButton();

  let activeConflict: ConflictBanner | null = null;

  async function enterConflictMode(): Promise<void> {
    // Avoid stacking banners; the first one wins until dismissed.
    if (activeConflict !== null) return;

    let fresh;
    try {
      fresh = await api.loadTemplate(boot.corpusId, boot.relPath);
    } catch (err) {
      showToast(ui.toast, `Couldn't read fresh disk text: ${(err as Error).message}`, "err");
      return;
    }
    if (fresh.base_hash === baseHash) {
      // The WS told us about a change but the hash matches — already
      // settled. Likely race with our own save. Quietly drop the banner.
      return;
    }

    const editorText = editor!.view.state.doc.toString();
    if (editorText === baseText) {
      // No local edits to preserve — just rebase silently. The user
      // sees the file refresh; no decision to make.
      acceptDiskAsBase(fresh.text, fresh.base_hash);
      return;
    }

    activeConflict = showConflict({
      banner: ui.banner,
      modalParent: document.body,
      baseText,
      diskText: fresh.text,
      editorText,
      diskBaseHash: fresh.base_hash,
      onReload: () => {
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
        ui.status.textContent = `reloaded · base ${baseHash}`;
        refreshSaveButton();
        activeConflict = null;
      },
      onKeep: () => {
        // Keep local edits but rebase to the new disk hash so the next
        // save doesn't immediately 409. The diff base stays at the old
        // base so the gutter still reflects the user's intent.
        baseHash = fresh.base_hash;
        ui.status.textContent = `kept local · base ${baseHash}`;
        activeConflict = null;
      },
      onResolve: (mergedText, newBaseHash) => {
        baseText = mergedText;
        baseHash = newBaseHash;
        doc.setText(mergedText);
        suppressEditorChange = true;
        editor!.setText(mergedText);
        editor!.setBase(mergedText);
        suppressEditorChange = false;
        suppressFormRefresh = true;
        form.refresh();
        suppressFormRefresh = false;
        ui.status.textContent = `merged · base ${baseHash}`;
        showToast(ui.toast, "Conflicts resolved. Review the editor and save.");
        refreshSaveButton();
        activeConflict = null;
      },
    });
  }

  function acceptDiskAsBase(diskText: string, diskBaseHash: string): void {
    baseText = diskText;
    baseHash = diskBaseHash;
    doc.setText(diskText);
    suppressEditorChange = true;
    editor!.setText(diskText);
    editor!.setBase(diskText);
    suppressEditorChange = false;
    suppressFormRefresh = true;
    form.refresh();
    suppressFormRefresh = false;
    ui.status.textContent = `synced · base ${baseHash}`;
    refreshSaveButton();
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
        void enterConflictMode();
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
      onConflict: () => {
        void enterConflictMode();
      },
    });
  }

  ui.saveBtn.addEventListener("click", () => void openSave());

  const ws: WsClient = openEditorWebSocket({
    corpusId: boot.corpusId,
    relPath: boot.relPath,
    onEvent: (event) => {
      if (event.type === "file_changed") {
        // Ignore events whose new_hash matches our current base — that
        // means the change came from us (post-save rebase) and is a
        // no-op. Rare race: server re-emits before our save response
        // returns; the hash check guards both sides.
        if (event.new_hash === baseHash) return;
        void enterConflictMode();
      } else if (event.type === "duplicate_session") {
        isDuplicateTab = true;
        completions.invalidateCache();
        renderAdvisories();
        ui.saveBtn.disabled = true;
        ui.saveBtn.title = "Read-only: another tab owns this file";
      }
    },
  });

  // Cmd/Ctrl-S opens the save modal. Trap before the browser does.
  // Cmd/Ctrl-K is a placeholder for the v2 command palette — for now
  // we just acknowledge the keystroke with a toast so users learn the
  // shortcut exists.
  window.addEventListener("keydown", (ev) => {
    if ((ev.metaKey || ev.ctrlKey) && ev.key === "s") {
      ev.preventDefault();
      if (!ui.saveBtn.disabled) void openSave();
      return;
    }
    if ((ev.metaKey || ev.ctrlKey) && ev.key === "k") {
      ev.preventDefault();
      showToast(ui.toast, "Command palette: coming in v2.");
    }
  });

  window.addEventListener("beforeunload", (ev) => {
    if (isDuplicateTab) return;
    if (editor && editor.view.state.doc.toString() !== baseText) {
      ev.preventDefault();
      ev.returnValue = "";
    }
  });

  window.addEventListener("pagehide", () => {
    ws.close();
  });

  // Expose a tiny debug handle for live verification (preview_eval).
  // Not used by production code paths.
  (window as unknown as { __attuneEditor?: unknown }).__attuneEditor = {
    api,
    doc,
    editor,
    ws,
    invalidateCompletions: completions.invalidateCache,
    save: openSave,
    reload: reloadFromDisk,
    triggerConflict: enterConflictMode,
    openRename,
    switcher,
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
