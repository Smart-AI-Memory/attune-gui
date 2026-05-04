/**
 * Template editor entry point.
 *
 * Bootstraps the layout (top bar, frontmatter sidebar, editor pane,
 * diagnostics strip), reads the corpus + path bootstrap data from the
 * Jinja shell, fetches the template via the API, and mounts CodeMirror
 * with the linter + autocomplete extensions.
 */

import "./style.css";
import { EditorApi, ApiError } from "./api";
import { TemplateDocument } from "./document-model";
import { mountEditor, type MountedEditor } from "./editor";
import { renderFrontmatterForm } from "./frontmatter-form";
import { attuneLinter } from "./lint";
import { renderDiagnosticsStrip } from "./diagnostics-strip";
import { attuneCompletions } from "./autocomplete";

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

function buildLayout(root: HTMLElement): {
  status: HTMLElement;
  pathLabel: HTMLElement;
  formSidebar: HTMLElement;
  editorPane: HTMLElement;
  diagnostics: HTMLElement;
} {
  root.innerHTML = "";
  root.classList.add("attune-editor-shell");

  const topBar = document.createElement("header");
  topBar.className = "attune-editor-topbar";
  const status = document.createElement("span");
  status.className = "attune-editor-status";
  const pathLabel = document.createElement("span");
  pathLabel.className = "attune-editor-path";
  topBar.appendChild(pathLabel);
  topBar.appendChild(status);

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

  root.appendChild(topBar);
  root.appendChild(main);
  root.appendChild(diagnostics);

  return { status, pathLabel, formSidebar, editorPane, diagnostics };
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

  editor = mountEditor({
    parent: ui.editorPane,
    initialText: template.text,
    baseText: template.text,
    extra: [linter, completions.extension],
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

  // Expose a tiny debug handle for live verification (preview_eval).
  // Not used by production code paths.
  (window as unknown as { __attuneEditor?: unknown }).__attuneEditor = {
    api,
    doc,
    editor,
    invalidateCompletions: completions.invalidateCache,
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
