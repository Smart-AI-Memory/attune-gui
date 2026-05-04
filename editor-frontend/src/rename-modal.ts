/**
 * Rename refactor modal (M4 #21).
 *
 * Triggered from the frontmatter-form chip context menu (right-click
 * on a tag/alias chip → "Rename …"). The modal:
 *
 *   1. Asks the user for the new name.
 *   2. Calls ``/refactor/rename/preview`` debounced 250ms after each
 *      keystroke to render a multi-file diff.
 *   3. Disables Apply until preview returns at least one file edit.
 *   4. On Apply, posts ``/refactor/rename/apply`` and reports affected
 *      files via ``onSuccess``.
 *
 * Server contract:
 *   - 200 → ``RenamePlan`` (preview) or ``{affected_files, plan}`` (apply).
 *   - 409 → name collision (alias kind only) — surfaced as a banner
 *     with the conflicting template path.
 *   - 400 → unsupported kind (template_path is reserved for v2).
 *
 * The host wires:
 *   - ``onSuccess(affected)`` so the editor can broadcast a refresh
 *     and show a toast.
 */

import { ApiError, type EditorApi, type RenameFileEdit, type RenameKind, type RenamePlan } from "./api";

export interface RenameModalOptions {
  api: EditorApi;
  corpusId: string;
  /** What kind of name we're renaming — drives label text + endpoint. */
  kind: RenameKind;
  /** The current name, prefilled into the "from" input. */
  currentName: string;
  /** DOM parent for the modal overlay. Usually `document.body`. */
  parent: HTMLElement;
  /** Fired after a successful apply. */
  onSuccess(affected: string[], plan: RenamePlan): void;
  /** Fired when the modal closes for any reason. */
  onClose?(): void;
}

export interface RenameModal {
  close(): void;
}

const KIND_LABELS: Record<RenameKind, { noun: string; field: string }> = {
  alias: { noun: "alias", field: "Aliases" },
  tag: { noun: "tag", field: "Tags" },
  template_path: { noun: "template path", field: "Path" },
};

export function openRenameModal(opts: RenameModalOptions): RenameModal {
  const labels = KIND_LABELS[opts.kind];

  const overlay = document.createElement("div");
  overlay.className = "attune-modal-overlay";
  const dialog = document.createElement("div");
  dialog.className = "attune-modal attune-modal-rename";
  dialog.setAttribute("role", "dialog");
  dialog.setAttribute("aria-modal", "true");
  dialog.setAttribute("aria-label", `Rename ${labels.noun}`);
  overlay.appendChild(dialog);

  const head = document.createElement("header");
  head.className = "attune-modal-head";
  head.textContent = `Rename ${labels.noun}`;
  dialog.appendChild(head);

  const inputsRow = document.createElement("div");
  inputsRow.className = "attune-rename-inputs";

  const fromLabel = document.createElement("label");
  fromLabel.className = "attune-fm-label";
  fromLabel.textContent = "From";
  const fromInput = document.createElement("input");
  fromInput.className = "attune-fm-input";
  fromInput.value = opts.currentName;
  fromInput.disabled = true;

  const toLabel = document.createElement("label");
  toLabel.className = "attune-fm-label";
  toLabel.textContent = "To";
  const toInput = document.createElement("input");
  toInput.className = "attune-fm-input";
  toInput.placeholder = `New ${labels.noun} name…`;
  toInput.autocomplete = "off";
  toInput.spellcheck = false;

  inputsRow.appendChild(fromLabel);
  inputsRow.appendChild(fromInput);
  inputsRow.appendChild(toLabel);
  inputsRow.appendChild(toInput);
  dialog.appendChild(inputsRow);

  const banner = document.createElement("div");
  banner.className = "attune-modal-lint";
  banner.hidden = true;
  dialog.appendChild(banner);

  const summary = document.createElement("div");
  summary.className = "attune-rename-summary";
  summary.textContent = "Type a new name to preview affected files.";
  dialog.appendChild(summary);

  const body = document.createElement("div");
  body.className = "attune-modal-body";
  dialog.appendChild(body);

  const footer = document.createElement("footer");
  footer.className = "attune-modal-foot";
  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.className = "attune-btn attune-btn-secondary";
  cancelBtn.textContent = "Cancel";
  const applyBtn = document.createElement("button");
  applyBtn.type = "button";
  applyBtn.className = "attune-btn attune-btn-primary";
  applyBtn.textContent = "Apply rename";
  applyBtn.disabled = true;
  footer.appendChild(cancelBtn);
  footer.appendChild(applyBtn);
  dialog.appendChild(footer);

  let previewToken = 0;
  let lastPreview: RenamePlan | null = null;
  let previewTimer: ReturnType<typeof setTimeout> | null = null;
  let busy = false;

  function setBanner(message: string | null, kind: "error" | "info" = "error"): void {
    if (message === null) {
      banner.hidden = true;
      banner.textContent = "";
      banner.className = "attune-modal-lint";
      return;
    }
    banner.hidden = false;
    banner.textContent = message;
    banner.className =
      kind === "info"
        ? "attune-modal-advisory"
        : "attune-modal-lint";
  }

  function renderPlan(plan: RenamePlan): void {
    body.innerHTML = "";
    lastPreview = plan;
    if (plan.edits.length === 0) {
      summary.textContent = `No references to "${plan.old}" found in this corpus — apply will be a no-op.`;
      applyBtn.disabled = true;
      return;
    }
    const totalHunks = plan.edits.reduce((n, e) => n + e.hunks.length, 0);
    summary.textContent = `Renaming "${plan.old}" → "${plan.new}" affects ${plan.edits.length} file${plan.edits.length === 1 ? "" : "s"} (${totalHunks} hunk${totalHunks === 1 ? "" : "s"}).`;
    for (const edit of plan.edits) body.appendChild(renderFileEdit(edit));
    applyBtn.disabled = false;
  }

  function schedulePreview(): void {
    if (previewTimer !== null) clearTimeout(previewTimer);
    const newName = toInput.value.trim();
    if (newName === "" || newName === opts.currentName) {
      summary.textContent =
        newName === ""
          ? "Type a new name to preview affected files."
          : "New name is the same as the old name.";
      body.innerHTML = "";
      applyBtn.disabled = true;
      lastPreview = null;
      setBanner(null);
      return;
    }
    previewTimer = setTimeout(() => {
      void runPreview(newName);
    }, 250);
  }

  async function runPreview(newName: string): Promise<void> {
    const myToken = ++previewToken;
    try {
      const plan = await opts.api.renamePreview(opts.corpusId, {
        old: opts.currentName,
        new: newName,
        kind: opts.kind,
      });
      if (myToken !== previewToken) return;
      setBanner(null);
      renderPlan(plan);
    } catch (err) {
      if (myToken !== previewToken) return;
      lastPreview = null;
      applyBtn.disabled = true;
      body.innerHTML = "";
      const detail = renameErrorMessage(err);
      setBanner(detail);
    }
  }

  toInput.addEventListener("input", schedulePreview);
  toInput.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") {
      ev.preventDefault();
      if (!applyBtn.disabled) void doApply();
    }
  });

  function close(): void {
    if (previewTimer !== null) clearTimeout(previewTimer);
    document.removeEventListener("keydown", onKey);
    overlay.remove();
    opts.onClose?.();
  }

  function onKey(ev: KeyboardEvent): void {
    if (ev.key === "Escape") close();
  }
  document.addEventListener("keydown", onKey);

  cancelBtn.addEventListener("click", close);

  async function doApply(): Promise<void> {
    if (busy || lastPreview === null) return;
    busy = true;
    applyBtn.disabled = true;
    applyBtn.textContent = "Applying…";
    try {
      const res = await opts.api.renameApply(opts.corpusId, {
        old: lastPreview.old,
        new: lastPreview.new,
        kind: opts.kind,
      });
      opts.onSuccess(res.affected_files, res.plan);
      close();
    } catch (err) {
      busy = false;
      applyBtn.textContent = "Apply rename";
      applyBtn.disabled = false;
      setBanner(renameErrorMessage(err));
    }
  }

  applyBtn.addEventListener("click", () => void doApply());

  opts.parent.appendChild(overlay);
  // Focus the "to" input on next frame so the user can type immediately.
  queueMicrotask(() => toInput.focus());

  return { close };
}

function renderFileEdit(edit: RenameFileEdit): HTMLElement {
  const sec = document.createElement("section");
  sec.className = "attune-rename-file";

  const head = document.createElement("header");
  head.className = "attune-rename-file-head";
  head.textContent = edit.path;
  sec.appendChild(head);

  for (const hunk of edit.hunks) {
    const item = document.createElement("div");
    item.className = "attune-hunk";
    const itemHead = document.createElement("header");
    itemHead.className = "attune-hunk-head";
    const headerLine = document.createElement("span");
    headerLine.className = "attune-hunk-header-line";
    headerLine.textContent = hunk.header;
    itemHead.appendChild(headerLine);
    item.appendChild(itemHead);

    const pre = document.createElement("pre");
    pre.className = "attune-hunk-body";
    for (const raw of hunk.lines) {
      const span = document.createElement("span");
      const sym = raw[0];
      span.className =
        sym === "+"
          ? "attune-hunk-add"
          : sym === "-"
            ? "attune-hunk-del"
            : "attune-hunk-ctx";
      span.textContent = raw + "\n";
      pre.appendChild(span);
    }
    item.appendChild(pre);
    sec.appendChild(item);
  }
  return sec;
}

function renameErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 409 && isCollisionDetail(err.detail)) {
      const d = err.detail.detail;
      return `Name collision: "${d.message}" (owned by ${d.owning_path}).`;
    }
    if (err.status === 400) {
      return `Unsupported rename: ${describeApiDetail(err.detail) ?? "see server logs"}.`;
    }
    return `Server error ${err.status}: ${describeApiDetail(err.detail) ?? err.message}.`;
  }
  return `Network error: ${(err as Error).message}`;
}

interface CollisionEnvelope {
  detail: { code: string; message: string; owning_path: string };
}

function isCollisionDetail(value: unknown): value is CollisionEnvelope {
  if (typeof value !== "object" || value === null) return false;
  const detail = (value as { detail?: unknown }).detail;
  if (typeof detail !== "object" || detail === null) return false;
  const obj = detail as Record<string, unknown>;
  return (
    obj.code === "name_collision" &&
    typeof obj.message === "string" &&
    typeof obj.owning_path === "string"
  );
}

function describeApiDetail(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (typeof detail === "object" && detail !== null) {
    const obj = detail as Record<string, unknown>;
    if (typeof obj.detail === "string") return obj.detail;
    if (typeof obj.message === "string") return obj.message;
  }
  return null;
}
