/**
 * Per-hunk save modal.
 *
 * Opens when the user clicks Save. Shows each hunk with a checkbox
 * (default-checked) and a colored unified-diff body. As the user
 * toggles hunks the projected text is recomputed and lint runs against
 * it — the Save button is disabled when the projection has any
 * frontmatter parse errors so users can't write known-broken state.
 *
 * The host wires three callbacks:
 *
 *   - ``onLint(projected)`` runs the projected-state lint and resolves
 *     to a list of diagnostics.
 *   - ``onSave(acceptedIds)`` performs the atomic save.
 *   - ``onConflict()`` is invoked when ``onSave`` rejects with a 409.
 */

import { ApiError, type Hunk, type ServerDiagnostic } from "./api";
import { applyAcceptedHunks, saveButtonLabel } from "./save-flow";

export interface SaveModalBindings {
  parent: HTMLElement;
  baseText: string;
  hunks: readonly Hunk[];
  onLint(projected: string): Promise<ServerDiagnostic[]>;
  onSave(acceptedIds: string[]): Promise<void>;
  onConflict?(): void;
  onClose?(): void;
}

/** Diagnostic codes that block save (only frontmatter errors per spec). */
const BLOCKING_CODES = /^(missing-required|bad-enum|bad-type|too-short|duplicate-items|not-a-mapping|malformed-yaml)$/;

export interface SaveModal {
  close(): void;
}

export function openSaveModal(bindings: SaveModalBindings): SaveModal {
  const { parent, hunks, baseText, onLint, onSave, onConflict, onClose } = bindings;

  const overlay = document.createElement("div");
  overlay.className = "attune-modal-overlay";
  const dialog = document.createElement("div");
  dialog.className = "attune-modal";
  dialog.setAttribute("role", "dialog");
  dialog.setAttribute("aria-modal", "true");
  dialog.setAttribute("aria-label", "Save changes");
  overlay.appendChild(dialog);

  const header = document.createElement("header");
  header.className = "attune-modal-head";
  header.textContent = `Save changes — ${hunks.length} hunk${hunks.length === 1 ? "" : "s"}`;
  dialog.appendChild(header);

  const body = document.createElement("div");
  body.className = "attune-modal-body";
  dialog.appendChild(body);

  const lintBanner = document.createElement("div");
  lintBanner.className = "attune-modal-lint";
  lintBanner.hidden = true;
  dialog.appendChild(lintBanner);

  const advisoryBanner = document.createElement("div");
  advisoryBanner.className = "attune-modal-advisory";
  advisoryBanner.hidden = true;
  dialog.appendChild(advisoryBanner);

  const footer = document.createElement("footer");
  footer.className = "attune-modal-foot";
  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.textContent = "Cancel";
  cancelBtn.className = "attune-btn attune-btn-secondary";
  const saveBtn = document.createElement("button");
  saveBtn.type = "button";
  saveBtn.className = "attune-btn attune-btn-primary";
  footer.appendChild(cancelBtn);
  footer.appendChild(saveBtn);
  dialog.appendChild(footer);

  // Default-checked: every hunk on at open time.
  const accepted = new Set<string>(hunks.map((h) => h.hunk_id));
  const checkboxes = new Map<string, HTMLInputElement>();

  for (let i = 0; i < hunks.length; i += 1) {
    const hunk = hunks[i];
    const item = document.createElement("section");
    item.className = "attune-hunk";

    const head = document.createElement("header");
    head.className = "attune-hunk-head";

    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = true;
    cb.id = `attune-hunk-cb-${i}`;
    cb.dataset.hunkId = hunk.hunk_id;
    cb.addEventListener("change", () => {
      if (cb.checked) accepted.add(hunk.hunk_id);
      else accepted.delete(hunk.hunk_id);
      void refresh();
    });

    const lbl = document.createElement("label");
    lbl.htmlFor = cb.id;
    lbl.className = "attune-hunk-header-line";
    lbl.textContent = hunk.header;

    head.appendChild(cb);
    head.appendChild(lbl);

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

    item.appendChild(head);
    item.appendChild(pre);
    body.appendChild(item);
    checkboxes.set(hunk.hunk_id, cb);
  }

  let lintToken = 0;
  let blocked = false;

  async function refresh(): Promise<void> {
    const total = hunks.length;
    const labelInfo = saveButtonLabel(total, accepted.size);
    saveBtn.textContent = labelInfo.label;
    if (!labelInfo.enabled) {
      saveBtn.disabled = true;
      lintBanner.hidden = true;
      return;
    }

    const projected = applyAcceptedHunks(baseText, hunks, accepted);
    const myToken = ++lintToken;
    let diags: ServerDiagnostic[] = [];
    try {
      diags = await onLint(projected);
    } catch {
      // If lint fails, don't block save — the strip already shows the
      // server-down info diagnostic.
    }
    if (myToken !== lintToken) return;

    const isBlocking = (d: ServerDiagnostic) =>
      d.severity === "error" && BLOCKING_CODES.test(d.code);
    const blocking = diags.filter(isBlocking);
    // Advisory = error/warning that does NOT block (e.g. broken-alias).
    // Some drafts intentionally reference an alias the user is about
    // to create — we let that through with a clear heads-up rather
    // than hard-blocking the save.
    const advisory = diags.filter(
      (d) => (d.severity === "error" || d.severity === "warning") && !isBlocking(d),
    );

    blocked = blocking.length > 0;
    if (blocked) {
      lintBanner.hidden = false;
      lintBanner.innerHTML = "";
      const title = document.createElement("strong");
      title.textContent = `Cannot save — ${blocking.length} frontmatter error${blocking.length === 1 ? "" : "s"} in projected state:`;
      lintBanner.appendChild(title);
      const ul = document.createElement("ul");
      for (const d of blocking) {
        const li = document.createElement("li");
        li.textContent = `line ${d.line}: ${d.message}`;
        ul.appendChild(li);
      }
      lintBanner.appendChild(ul);
      saveBtn.disabled = true;
    } else {
      lintBanner.hidden = true;
      saveBtn.disabled = false;
    }

    if (advisory.length > 0) {
      advisoryBanner.hidden = false;
      advisoryBanner.innerHTML = "";
      const title = document.createElement("strong");
      title.textContent = `${advisory.length} advisory issue${advisory.length === 1 ? "" : "s"} — save will proceed:`;
      advisoryBanner.appendChild(title);
      const ul = document.createElement("ul");
      for (const d of advisory) {
        const li = document.createElement("li");
        li.textContent = `line ${d.line}: ${d.message}`;
        ul.appendChild(li);
      }
      advisoryBanner.appendChild(ul);
    } else {
      advisoryBanner.hidden = true;
    }
  }

  function close(): void {
    document.removeEventListener("keydown", onKey);
    overlay.remove();
    onClose?.();
  }

  function onKey(ev: KeyboardEvent): void {
    if (ev.key === "Escape") close();
    if (ev.key === "Enter" && (ev.metaKey || ev.ctrlKey)) {
      ev.preventDefault();
      void doSave();
    }
  }
  document.addEventListener("keydown", onKey);

  cancelBtn.addEventListener("click", close);

  async function doSave(): Promise<void> {
    if (blocked || accepted.size === 0) return;
    saveBtn.disabled = true;
    try {
      await onSave([...accepted]);
      close();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        onConflict?.();
        close();
        return;
      }
      lintBanner.hidden = false;
      lintBanner.innerHTML = "";
      const msg = document.createElement("strong");
      msg.textContent = `Save failed: ${(err as Error).message}`;
      lintBanner.appendChild(msg);
      saveBtn.disabled = false;
    }
  }

  saveBtn.addEventListener("click", () => void doSave());

  parent.appendChild(overlay);
  void refresh();
  return { close };
}
