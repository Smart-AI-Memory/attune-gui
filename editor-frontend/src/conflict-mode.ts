/**
 * Conflict mode UI — three-pane merge resolver.
 *
 * Triggered by either:
 *   - a WebSocket ``file_changed`` event while the user has unsaved
 *     edits, or
 *   - a 409 from the save endpoint (the file moved underneath us).
 *
 * Layout:
 *   - A non-dismissible banner at the top of the editor with three
 *     buttons: Reload, Keep, Resolve.
 *   - "Resolve" opens a modal showing each merge region. Auto-merged
 *     regions render as collapsed context. Conflict regions show
 *     base / disk / editor side-by-side with a chooser (`disk`,
 *     `editor`, or `both`).
 *   - "Done" enables only when every conflict has a choice. It calls
 *     ``onResolve(mergedText, newBaseHash)`` so the host can install
 *     the merged text into the editor and reset the diff base.
 *
 * The host is responsible for the actual save — this module produces
 * a merged text and lets the editor continue. Per-region accept/keep
 * is a *resolution* decision, not a *commit* decision.
 */

import {
  threeWayMerge,
  applyResolutions,
  preferredTrailingNewline,
  summarize,
  type ConflictChoice,
  type MergeRegion,
} from "./three-way-merge";

export interface ConflictBanner {
  /** Tear down the banner and any open resolve modal. */
  close(): void;
  /** True iff a resolve modal is currently open. */
  isResolving(): boolean;
}

export interface ShowConflictOptions {
  /** Element to mount the banner into (typically the editor's header strip). */
  banner: HTMLElement;
  /** Element to mount the resolve modal into (typically `document.body`). */
  modalParent: HTMLElement;
  /** Common ancestor — the version both sides started from. */
  baseText: string;
  /** Current on-disk text. */
  diskText: string;
  /** Current text in the editor pane. */
  editorText: string;
  /** New base hash from disk — passed back when the user resolves. */
  diskBaseHash: string;
  /**
   * Reload from disk: throw away local edits and replace with `diskText`.
   * Banner closes after the host completes.
   */
  onReload(): void;
  /**
   * Keep local edits: dismiss the banner without reloading. The host
   * remains free to save; the editor's `base_hash` is unchanged.
   */
  onKeep(): void;
  /**
   * Resolved: install ``mergedText`` into the editor and rebase the
   * diff base to ``diskBaseHash``. The user may then save normally.
   */
  onResolve(mergedText: string, diskBaseHash: string): void;
}

export function showConflict(opts: ShowConflictOptions): ConflictBanner {
  const merge = threeWayMerge(opts.diskText, opts.baseText, opts.editorText);
  const stats = summarize(merge);
  const hasConflict = merge.hasConflict;

  // Header banner
  const wrap = document.createElement("div");
  wrap.className = "attune-banner attune-banner-conflict";

  const msg = document.createElement("span");
  msg.className = "attune-banner-msg";
  msg.textContent = hasConflict
    ? `This file changed on disk. ${stats.conflicts} conflict${stats.conflicts === 1 ? "" : "s"} need your decision.`
    : "This file changed on disk. Your edits don't overlap — you can reload, keep, or auto-merge.";

  const reloadBtn = document.createElement("button");
  reloadBtn.type = "button";
  reloadBtn.className = "attune-btn attune-btn-secondary";
  reloadBtn.textContent = "Reload from disk";

  const keepBtn = document.createElement("button");
  keepBtn.type = "button";
  keepBtn.className = "attune-btn attune-btn-secondary";
  keepBtn.textContent = "Keep local";

  const resolveBtn = document.createElement("button");
  resolveBtn.type = "button";
  resolveBtn.className = "attune-btn attune-btn-primary";
  resolveBtn.textContent = hasConflict ? "Resolve…" : "Auto-merge";

  wrap.appendChild(msg);
  wrap.appendChild(reloadBtn);
  wrap.appendChild(keepBtn);
  wrap.appendChild(resolveBtn);

  opts.banner.hidden = false;
  opts.banner.innerHTML = "";
  opts.banner.appendChild(wrap);

  let modal: ResolveModal | null = null;

  function close(): void {
    if (modal !== null) {
      modal.close();
      modal = null;
    }
    if (wrap.parentElement === opts.banner) {
      opts.banner.removeChild(wrap);
    }
    opts.banner.hidden = opts.banner.children.length === 0;
  }

  reloadBtn.addEventListener("click", () => {
    opts.onReload();
    close();
  });
  keepBtn.addEventListener("click", () => {
    opts.onKeep();
    close();
  });
  resolveBtn.addEventListener("click", () => {
    if (!hasConflict) {
      // No conflicts: apply auto-merge directly.
      const merged = applyResolutions(
        merge.regions,
        {},
        preferredTrailingNewline(opts.diskText, opts.baseText, opts.editorText),
      );
      opts.onResolve(merged, opts.diskBaseHash);
      close();
      return;
    }
    if (modal !== null) return;
    modal = openResolveModal({
      parent: opts.modalParent,
      regions: merge.regions,
      trailingNewline: preferredTrailingNewline(
        opts.diskText,
        opts.baseText,
        opts.editorText,
      ),
      onResolve: (merged) => {
        opts.onResolve(merged, opts.diskBaseHash);
        close();
      },
      onCancel: () => {
        modal = null;
      },
    });
  });

  return {
    close,
    isResolving(): boolean {
      return modal !== null;
    },
  };
}

interface ResolveModal {
  close(): void;
}

interface ResolveModalOptions {
  parent: HTMLElement;
  regions: readonly MergeRegion[];
  trailingNewline: boolean;
  onResolve(mergedText: string): void;
  onCancel(): void;
}

function openResolveModal(opts: ResolveModalOptions): ResolveModal {
  const overlay = document.createElement("div");
  overlay.className = "attune-modal-overlay";
  const dialog = document.createElement("div");
  dialog.className = "attune-modal attune-modal-conflict";
  dialog.setAttribute("role", "dialog");
  dialog.setAttribute("aria-modal", "true");
  dialog.setAttribute("aria-label", "Resolve conflicts");
  overlay.appendChild(dialog);

  const head = document.createElement("header");
  head.className = "attune-modal-head";
  head.textContent = "Resolve conflicts";
  dialog.appendChild(head);

  const body = document.createElement("div");
  body.className = "attune-modal-body";
  dialog.appendChild(body);

  const choices: Record<string, ConflictChoice | undefined> = {};
  let conflictCount = 0;
  const conflictRegions: Array<Extract<MergeRegion, { kind: "conflict" }>> = [];
  for (const region of opts.regions) {
    if (region.kind === "conflict") {
      conflictRegions.push(region);
      conflictCount++;
    }
  }

  for (const region of opts.regions) {
    if (region.kind === "auto") {
      const ctx = renderAutoRegion(region.lines);
      body.appendChild(ctx);
    } else {
      const block = renderConflictRegion(region, (choice) => {
        choices[region.id] = choice;
        refreshFooter();
      });
      body.appendChild(block);
    }
  }

  const footer = document.createElement("footer");
  footer.className = "attune-modal-foot";
  const status = document.createElement("span");
  status.className = "attune-modal-status";
  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.className = "attune-btn attune-btn-secondary";
  cancelBtn.textContent = "Cancel";
  const doneBtn = document.createElement("button");
  doneBtn.type = "button";
  doneBtn.className = "attune-btn attune-btn-primary";
  doneBtn.textContent = "Done";
  doneBtn.disabled = true;
  footer.appendChild(status);
  footer.appendChild(cancelBtn);
  footer.appendChild(doneBtn);
  dialog.appendChild(footer);

  function refreshFooter(): void {
    const made = conflictRegions.filter((r) => choices[r.id] !== undefined).length;
    status.textContent = `${made} of ${conflictCount} resolved`;
    doneBtn.disabled = made !== conflictCount;
  }
  refreshFooter();

  function close(): void {
    document.removeEventListener("keydown", onKey);
    overlay.remove();
  }

  function onKey(ev: KeyboardEvent): void {
    if (ev.key === "Escape") {
      close();
      opts.onCancel();
    }
  }
  document.addEventListener("keydown", onKey);

  cancelBtn.addEventListener("click", () => {
    close();
    opts.onCancel();
  });

  doneBtn.addEventListener("click", () => {
    if (doneBtn.disabled) return;
    const resolved: Record<string, ConflictChoice> = {};
    for (const r of conflictRegions) {
      // Defended above: refreshFooter only enables Done when all are set.
      const c = choices[r.id];
      if (c !== undefined) resolved[r.id] = c;
    }
    const merged = applyResolutions(
      opts.regions,
      resolved,
      opts.trailingNewline,
    );
    close();
    opts.onResolve(merged);
  });

  opts.parent.appendChild(overlay);
  return { close };
}

function renderAutoRegion(lines: readonly string[]): HTMLElement {
  const sec = document.createElement("section");
  sec.className = "attune-conflict-auto";
  const summary = document.createElement("div");
  summary.className = "attune-conflict-auto-head";
  summary.textContent = `${lines.length} line${lines.length === 1 ? "" : "s"} unchanged`;
  sec.appendChild(summary);
  // Show first/last lines as a hint, fully expandable on click.
  const pre = document.createElement("pre");
  pre.className = "attune-conflict-auto-body";
  pre.textContent =
    lines.length <= 6
      ? lines.join("\n")
      : `${lines.slice(0, 3).join("\n")}\n  …\n${lines.slice(-2).join("\n")}`;
  sec.appendChild(pre);
  return sec;
}

function renderConflictRegion(
  region: Extract<MergeRegion, { kind: "conflict" }>,
  onChoice: (choice: ConflictChoice) => void,
): HTMLElement {
  const sec = document.createElement("section");
  sec.className = "attune-conflict-region";
  sec.dataset.regionId = region.id;

  const head = document.createElement("header");
  head.className = "attune-conflict-head";
  head.textContent = `Conflict ${region.id}`;
  sec.appendChild(head);

  const panes = document.createElement("div");
  panes.className = "attune-conflict-panes";

  panes.appendChild(renderPane("Disk", region.diskLines, "attune-pane-disk"));
  panes.appendChild(renderPane("Base", region.baseLines, "attune-pane-base"));
  panes.appendChild(
    renderPane("Editor", region.editorLines, "attune-pane-editor"),
  );

  sec.appendChild(panes);

  const ctrls = document.createElement("div");
  ctrls.className = "attune-conflict-controls";
  ctrls.setAttribute("role", "radiogroup");
  ctrls.setAttribute("aria-label", `Resolution for ${region.id}`);

  const groupName = `attune-conflict-${region.id}`;
  const buttons: Array<{ choice: ConflictChoice; label: string }> = [
    { choice: "disk", label: "Use disk" },
    { choice: "editor", label: "Use editor" },
    { choice: "both", label: "Keep both" },
  ];

  for (const { choice, label } of buttons) {
    const id = `${groupName}-${choice}`;
    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = groupName;
    radio.id = id;
    radio.value = choice;
    radio.addEventListener("change", () => {
      if (radio.checked) {
        sec.dataset.choice = choice;
        onChoice(choice);
      }
    });
    const lbl = document.createElement("label");
    lbl.htmlFor = id;
    lbl.textContent = label;
    ctrls.appendChild(radio);
    ctrls.appendChild(lbl);
  }
  sec.appendChild(ctrls);

  return sec;
}

function renderPane(
  title: string,
  lines: readonly string[],
  cls: string,
): HTMLElement {
  const pane = document.createElement("div");
  pane.className = `attune-pane ${cls}`;
  const h = document.createElement("div");
  h.className = "attune-pane-head";
  h.textContent = title;
  const pre = document.createElement("pre");
  pre.className = "attune-pane-body";
  pre.textContent = lines.length === 0 ? "(empty)" : lines.join("\n");
  pane.appendChild(h);
  pane.appendChild(pre);
  return pane;
}
