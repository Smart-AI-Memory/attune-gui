/**
 * Corpus switcher (M4 #22).
 *
 * Renders a button in the top bar that opens a dropdown listing every
 * registered corpus. The dropdown:
 *
 *   - Highlights the currently active corpus.
 *   - Surfaces an inline search input once there are more than
 *     ``SEARCH_THRESHOLD`` corpora.
 *   - Has an "Add corpus…" entry at the bottom that opens a small
 *     modal for `name + path + kind`, calling ``/api/corpus/register``.
 *
 * The host owns the unsaved-edits guard (``onSwitchRequested``):
 * before a switch actually happens it can prompt Save / Discard /
 * Cancel and decide whether to proceed. The switcher only handles the
 * happy path (set active, navigate, refresh list).
 */

import type {
  CorpusEntry,
  CorpusKind,
  CorpusListResponse,
  EditorApi,
} from "./api";

const SEARCH_THRESHOLD = 10;

export interface SwitcherOptions {
  api: EditorApi;
  /** Top-bar element where the trigger button mounts. */
  trigger: HTMLElement;
  /** Element that holds the dropdown panel — typically `document.body`. */
  panelParent: HTMLElement;
  /** Modal parent — typically `document.body`. */
  modalParent: HTMLElement;
  /** Currently active corpus id (from the page bootstrap). */
  initialCorpusId: string;
  /** Initial path label, shown alongside the corpus name. */
  initialPath: string;
  /**
   * Called when the user picks a corpus that's *not* the active one.
   * The host must return ``true`` to proceed (e.g., after the user
   * confirms unsaved edits) or ``false`` to keep the current state.
   *
   * Returning a Promise lets the host show a Save/Discard/Cancel
   * dialog asynchronously.
   */
  onSwitchRequested: (target: CorpusEntry) => boolean | Promise<boolean>;
  /** Called after a successful switch so the host can navigate. */
  onSwitched: (target: CorpusEntry) => void;
  /** Optional: called when ``setActiveCorpus`` rejects so the host can toast. */
  onError?: (err: unknown) => void;
}

export interface CorpusSwitcher {
  /** Force-refresh the list (e.g., after a register elsewhere). */
  refresh(): Promise<void>;
  /** Tear down the trigger + any open dropdown. */
  destroy(): void;
}

export function mountCorpusSwitcher(opts: SwitcherOptions): CorpusSwitcher {
  let corpora: CorpusEntry[] = [];
  // ``currentCorpusId`` is the corpus this tab is *editing* — fixed
  // at page load and reflected in the trigger label.
  // ``registryActiveId`` is whichever corpus ``attune edit`` will pick
  // next; it can drift away from ``currentCorpusId`` when the user
  // opens an editor for a non-active corpus directly.
  const currentCorpusId: string | null = opts.initialCorpusId || null;
  let registryActiveId: string | null = opts.initialCorpusId || null;
  let panel: HTMLElement | null = null;
  let panelInput: HTMLInputElement | null = null;

  const button = document.createElement("button");
  button.type = "button";
  button.className = "attune-corpus-switcher";
  button.setAttribute("aria-haspopup", "menu");
  button.setAttribute("aria-expanded", "false");

  const labelEl = document.createElement("span");
  labelEl.className = "attune-corpus-switcher-label";
  const caretEl = document.createElement("span");
  caretEl.className = "attune-corpus-switcher-caret";
  caretEl.textContent = "▾";
  caretEl.setAttribute("aria-hidden", "true");
  button.appendChild(labelEl);
  button.appendChild(caretEl);

  opts.trigger.innerHTML = "";
  opts.trigger.appendChild(button);

  function renderLabel(): void {
    const current = corpora.find((c) => c.id === currentCorpusId);
    const corpusName = current?.name ?? currentCorpusId ?? "no corpus";
    labelEl.textContent = opts.initialPath
      ? `${corpusName} · ${opts.initialPath}`
      : corpusName;
  }
  renderLabel();

  function closePanel(): void {
    if (panel === null) return;
    panel.remove();
    panel = null;
    panelInput = null;
    button.setAttribute("aria-expanded", "false");
    document.removeEventListener("click", onDocClick, true);
    document.removeEventListener("keydown", onKey);
  }

  function onDocClick(ev: MouseEvent): void {
    const target = ev.target as Node | null;
    if (panel === null) return;
    if (target && (panel.contains(target) || button.contains(target))) return;
    closePanel();
  }

  function onKey(ev: KeyboardEvent): void {
    if (ev.key === "Escape") closePanel();
  }

  async function openPanel(): Promise<void> {
    if (panel !== null) {
      closePanel();
      return;
    }
    await refresh();

    const rect = button.getBoundingClientRect();
    panel = document.createElement("div");
    panel.className = "attune-corpus-panel";
    panel.setAttribute("role", "menu");
    panel.style.position = "absolute";
    panel.style.top = `${Math.round(rect.bottom + window.scrollY + 4)}px`;
    panel.style.left = `${Math.round(rect.left + window.scrollX)}px`;
    panel.style.minWidth = `${Math.max(280, rect.width)}px`;

    if (corpora.length > SEARCH_THRESHOLD) {
      const search = document.createElement("input");
      search.type = "search";
      search.placeholder = "Search corpora…";
      search.className = "attune-corpus-search";
      search.autocomplete = "off";
      search.spellcheck = false;
      search.addEventListener("input", () => renderList(search.value));
      panel.appendChild(search);
      panelInput = search;
    }

    const list = document.createElement("div");
    list.className = "attune-corpus-list";
    panel.appendChild(list);

    const addBtn = document.createElement("button");
    addBtn.type = "button";
    addBtn.className = "attune-corpus-add";
    addBtn.textContent = "+ Add corpus…";
    addBtn.addEventListener("click", () => {
      closePanel();
      openAddModal();
    });
    panel.appendChild(addBtn);

    opts.panelParent.appendChild(panel);
    button.setAttribute("aria-expanded", "true");

    function renderList(filter: string): void {
      list.innerHTML = "";
      const needle = filter.trim().toLowerCase();
      const visible = corpora.filter((c) => {
        if (!needle) return true;
        return (
          c.name.toLowerCase().includes(needle) ||
          c.id.toLowerCase().includes(needle) ||
          c.path.toLowerCase().includes(needle)
        );
      });
      if (visible.length === 0) {
        const empty = document.createElement("div");
        empty.className = "attune-corpus-empty";
        empty.textContent = "No matches.";
        list.appendChild(empty);
        return;
      }
      for (const c of visible) {
        const item = document.createElement("button");
        item.type = "button";
        item.className = "attune-corpus-item";
        if (c.id === registryActiveId) item.classList.add("attune-corpus-item-active");
        if (c.id === currentCorpusId) item.classList.add("attune-corpus-item-current");
        item.dataset.corpusId = c.id;
        const head = document.createElement("span");
        head.className = "attune-corpus-item-name";
        head.textContent = c.name;
        const sub = document.createElement("span");
        sub.className = "attune-corpus-item-path";
        sub.textContent = `${c.id} — ${c.path}`;
        item.appendChild(head);
        item.appendChild(sub);
        if (c.kind !== "source") {
          const tag = document.createElement("span");
          tag.className = `attune-corpus-kind attune-corpus-kind-${c.kind}`;
          tag.textContent = c.kind;
          item.appendChild(tag);
        }
        item.addEventListener("click", () => {
          void switchTo(c);
        });
        list.appendChild(item);
      }
    }

    renderList("");
    if (panelInput) queueMicrotask(() => panelInput?.focus());

    document.addEventListener("click", onDocClick, true);
    document.addEventListener("keydown", onKey);
  }

  async function switchTo(target: CorpusEntry): Promise<void> {
    if (target.id === currentCorpusId) {
      // Already editing this corpus — nothing to do.
      closePanel();
      return;
    }
    closePanel();
    const ok = await opts.onSwitchRequested(target);
    if (!ok) return;
    try {
      await opts.api.setActiveCorpus(target.id);
    } catch (err) {
      // Host stays on the current corpus and can retry.
      opts.onError?.(err);
      return;
    }
    registryActiveId = target.id;
    opts.onSwitched(target);
  }

  async function refresh(): Promise<void> {
    let res: CorpusListResponse;
    try {
      res = await opts.api.listCorpora();
    } catch {
      return;
    }
    corpora = res.corpora;
    registryActiveId = res.active;
    renderLabel();
  }

  function openAddModal(): void {
    openRegisterModal({
      api: opts.api,
      parent: opts.modalParent,
      onRegistered: async (entry) => {
        await refresh();
        // Don't auto-switch — the user said "add", not "switch to".
        // They'll pick it from the dropdown if they want.
        void entry;
      },
    });
  }

  button.addEventListener("click", () => {
    void openPanel();
  });

  // Initial fetch so the label resolves the friendly name.
  void refresh();

  return {
    refresh: () => refresh(),
    destroy(): void {
      closePanel();
      button.remove();
    },
  };
}

interface RegisterModalOptions {
  api: EditorApi;
  parent: HTMLElement;
  onRegistered(entry: CorpusEntry): void;
}

function openRegisterModal(opts: RegisterModalOptions): void {
  const overlay = document.createElement("div");
  overlay.className = "attune-modal-overlay";
  const dialog = document.createElement("div");
  dialog.className = "attune-modal attune-modal-register";
  dialog.setAttribute("role", "dialog");
  dialog.setAttribute("aria-modal", "true");
  dialog.setAttribute("aria-label", "Add corpus");
  overlay.appendChild(dialog);

  const head = document.createElement("header");
  head.className = "attune-modal-head";
  head.textContent = "Add corpus";
  dialog.appendChild(head);

  const body = document.createElement("div");
  body.className = "attune-modal-body attune-register-form";

  const nameRow = makeFieldRow("Name", "attune-register-name");
  const nameInput = nameRow.querySelector("input")!;
  nameInput.placeholder = "Friendly name (e.g., 'Help docs source')";

  const pathRow = makeFieldRow("Path", "attune-register-path");
  const pathInput = pathRow.querySelector("input")!;
  pathInput.placeholder = "Absolute path to template root";
  pathInput.spellcheck = false;
  pathInput.autocomplete = "off";

  const kindRow = document.createElement("div");
  kindRow.className = "attune-fm-row";
  const kindLbl = document.createElement("label");
  kindLbl.className = "attune-fm-label";
  kindLbl.textContent = "Kind";
  kindLbl.htmlFor = "attune-register-kind";
  const kindSel = document.createElement("select");
  kindSel.id = "attune-register-kind";
  kindSel.className = "attune-fm-input";
  for (const k of ["source", "generated", "ad-hoc"] as const) {
    const opt = document.createElement("option");
    opt.value = k;
    opt.textContent = k;
    kindSel.appendChild(opt);
  }
  kindRow.appendChild(kindLbl);
  kindRow.appendChild(kindSel);

  body.appendChild(nameRow);
  body.appendChild(pathRow);
  body.appendChild(kindRow);
  dialog.appendChild(body);

  const banner = document.createElement("div");
  banner.className = "attune-modal-lint";
  banner.hidden = true;
  dialog.appendChild(banner);

  const footer = document.createElement("footer");
  footer.className = "attune-modal-foot";
  const cancel = document.createElement("button");
  cancel.type = "button";
  cancel.className = "attune-btn attune-btn-secondary";
  cancel.textContent = "Cancel";
  const add = document.createElement("button");
  add.type = "button";
  add.className = "attune-btn attune-btn-primary";
  add.textContent = "Add corpus";
  add.disabled = true;
  footer.appendChild(cancel);
  footer.appendChild(add);
  dialog.appendChild(footer);

  function refreshDisabled(): void {
    add.disabled = !(nameInput.value.trim() && pathInput.value.trim());
  }
  nameInput.addEventListener("input", refreshDisabled);
  pathInput.addEventListener("input", refreshDisabled);

  function close(): void {
    document.removeEventListener("keydown", onKey);
    overlay.remove();
  }
  function onKey(ev: KeyboardEvent): void {
    if (ev.key === "Escape") close();
  }
  document.addEventListener("keydown", onKey);
  cancel.addEventListener("click", close);

  add.addEventListener("click", () => {
    void (async () => {
      add.disabled = true;
      add.textContent = "Adding…";
      banner.hidden = true;
      try {
        const entry = await opts.api.registerCorpus({
          name: nameInput.value.trim(),
          path: pathInput.value.trim(),
          kind: kindSel.value as CorpusKind,
        });
        opts.onRegistered(entry);
        close();
      } catch (err) {
        const msg = (err as Error).message;
        banner.hidden = false;
        banner.textContent = `Could not add corpus: ${msg}`;
        add.textContent = "Add corpus";
        add.disabled = false;
      }
    })();
  });

  opts.parent.appendChild(overlay);
  queueMicrotask(() => nameInput.focus());
}

function makeFieldRow(label: string, id: string): HTMLElement {
  const row = document.createElement("div");
  row.className = "attune-fm-row";
  const lbl = document.createElement("label");
  lbl.className = "attune-fm-label";
  lbl.textContent = label;
  lbl.htmlFor = id;
  const input = document.createElement("input");
  input.type = "text";
  input.id = id;
  input.className = "attune-fm-input";
  row.appendChild(lbl);
  row.appendChild(input);
  return row;
}

/**
 * Tiny Save/Discard/Cancel modal used by the host before switching
 * corpora when there are unsaved edits. Returned promise resolves to
 * the user's decision or `null` for cancel.
 */
export function promptUnsavedEdits(
  parent: HTMLElement,
): Promise<"save" | "discard" | null> {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = "attune-modal-overlay";
    const dialog = document.createElement("div");
    dialog.className = "attune-modal attune-modal-unsaved";
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    overlay.appendChild(dialog);

    const head = document.createElement("header");
    head.className = "attune-modal-head";
    head.textContent = "Unsaved changes";
    dialog.appendChild(head);

    const body = document.createElement("div");
    body.className = "attune-modal-body";
    body.textContent =
      "You have unsaved edits in this template. What would you like to do?";
    dialog.appendChild(body);

    const footer = document.createElement("footer");
    footer.className = "attune-modal-foot";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "attune-btn attune-btn-secondary";
    cancel.textContent = "Cancel";
    const discard = document.createElement("button");
    discard.type = "button";
    discard.className = "attune-btn attune-btn-secondary";
    discard.textContent = "Discard";
    const save = document.createElement("button");
    save.type = "button";
    save.className = "attune-btn attune-btn-primary";
    save.textContent = "Save…";
    footer.appendChild(cancel);
    footer.appendChild(discard);
    footer.appendChild(save);
    dialog.appendChild(footer);

    function close(value: "save" | "discard" | null): void {
      document.removeEventListener("keydown", onKey);
      overlay.remove();
      resolve(value);
    }
    function onKey(ev: KeyboardEvent): void {
      if (ev.key === "Escape") close(null);
    }
    document.addEventListener("keydown", onKey);
    cancel.addEventListener("click", () => close(null));
    discard.addEventListener("click", () => close("discard"));
    save.addEventListener("click", () => close("save"));

    parent.appendChild(overlay);
  });
}
