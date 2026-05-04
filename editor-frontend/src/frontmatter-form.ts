/**
 * Schema-driven frontmatter form (M3 #16).
 *
 * The form reads ``template_schema.json`` (served at
 * ``/api/editor/template-schema``) and emits a typed input per
 * property:
 *
 *   - string with ``enum``  → ``<select>``
 *   - string with ``format: textarea`` or name in TEXTAREA_FIELDS
 *                            → ``<textarea>``
 *   - string                → ``<input type="text">``
 *   - array                 → chip input (pill list + add field)
 *
 * Required fields are marked. Unknown frontmatter fields (those not
 * present in ``schema.properties``) are surfaced as a read-only list
 * at the bottom of the form so they remain visible without inviting
 * accidental edits.
 *
 * The "Raw YAML" toggle replaces the form with a textarea showing the
 * frontmatter block. Edits in either view round-trip through the same
 * ``TemplateDocument`` instance, so the on-disk YAML produced by the
 * two paths is byte-identical.
 */

import type { TemplateDocument } from "./document-model";
import type { TemplateSchema, TemplateSchemaProperty } from "./api";

export type RenamableField = "tags" | "aliases";

export interface FormBindings {
  doc: TemplateDocument;
  schema: TemplateSchema;
  /** Called after every form edit so the caller can reflect into CM. */
  onChange: () => void;
  /**
   * Optional hook fired when the user picks "Rename …" from a chip's
   * context menu (right-click). Currently surfaced for `tags` and
   * `aliases`. The host opens the rename modal.
   */
  onRename?: (field: RenamableField, name: string) => void;
}

export interface FormHandle {
  refresh(): void;
}

const TEXTAREA_FIELDS = new Set(["summary"]);

interface FieldRenderer {
  refresh(): void;
}

function isArrayProperty(prop: TemplateSchemaProperty): boolean {
  if (prop.type === "array") return true;
  if (Array.isArray(prop.type) && prop.type.includes("array")) return true;
  return false;
}

function isTextareaField(name: string, prop: TemplateSchemaProperty): boolean {
  if (TEXTAREA_FIELDS.has(name)) return true;
  // Future: schema can carry an `x-attune-multiline: true` extension.
  return Boolean((prop as Record<string, unknown>)["x-attune-multiline"]);
}

function renderRow(parent: HTMLElement, label: string, required: boolean): HTMLElement {
  const row = document.createElement("div");
  row.className = "attune-fm-row";
  const lbl = document.createElement("label");
  lbl.className = "attune-fm-label";
  lbl.textContent = label;
  if (required) {
    const star = document.createElement("span");
    star.className = "attune-fm-required";
    star.textContent = " *";
    star.title = "Required";
    lbl.appendChild(star);
  }
  row.appendChild(lbl);
  parent.appendChild(row);
  return row;
}

function attachInput(
  row: HTMLElement,
  el: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement,
  id: string,
  prop: TemplateSchemaProperty,
): void {
  el.id = id;
  el.className = "attune-fm-input";
  if (prop.description) {
    el.title = prop.description;
  }
  const label = row.querySelector("label.attune-fm-label") as HTMLLabelElement | null;
  if (label) label.htmlFor = id;
  row.appendChild(el);
}

// -- Field renderers ---------------------------------------------------

function renderEnumField(
  parent: HTMLElement,
  doc: TemplateDocument,
  name: string,
  prop: TemplateSchemaProperty,
  required: boolean,
  onChange: () => void,
): FieldRenderer {
  const row = renderRow(parent, name, required);
  const select = document.createElement("select");
  if (!required) {
    const blank = document.createElement("option");
    blank.value = "";
    blank.textContent = "—";
    select.appendChild(blank);
  }
  for (const value of prop.enum ?? []) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = value;
    select.appendChild(opt);
  }
  attachInput(row, select, `attune-fm-${name}`, prop);
  select.addEventListener("change", () => {
    if (select.value === "" && !required) doc.removeField(name);
    else doc.setField(name, select.value);
    onChange();
  });
  return {
    refresh() {
      const v = doc.getField(name);
      select.value = typeof v === "string" ? v : "";
    },
  };
}

function renderStringField(
  parent: HTMLElement,
  doc: TemplateDocument,
  name: string,
  prop: TemplateSchemaProperty,
  required: boolean,
  onChange: () => void,
): FieldRenderer {
  const row = renderRow(parent, name, required);
  const isTextarea = isTextareaField(name, prop);
  const input = isTextarea
    ? document.createElement("textarea")
    : document.createElement("input");
  if (input instanceof HTMLInputElement) input.type = "text";
  if (input instanceof HTMLTextAreaElement) input.rows = 3;
  attachInput(row, input, `attune-fm-${name}`, prop);
  input.addEventListener("input", () => {
    const v = input.value;
    if (v === "" && !required) doc.removeField(name);
    else doc.setField(name, v);
    onChange();
  });
  return {
    refresh() {
      const v = doc.getField(name);
      input.value = typeof v === "string" ? v : "";
    },
  };
}

function renderArrayField(
  parent: HTMLElement,
  doc: TemplateDocument,
  name: string,
  prop: TemplateSchemaProperty,
  required: boolean,
  onChange: () => void,
  onRename?: (field: RenamableField, value: string) => void,
): FieldRenderer {
  const row = renderRow(parent, name, required);
  row.classList.add("attune-fm-row-chips");

  const chipBox = document.createElement("div");
  chipBox.className = "attune-fm-chips";

  const input = document.createElement("input");
  input.type = "text";
  input.className = "attune-fm-input attune-fm-chip-input";
  input.placeholder = "type and press Enter or , to add";
  input.id = `attune-fm-${name}`;
  if (prop.description) input.title = prop.description;
  const label = row.querySelector("label.attune-fm-label") as HTMLLabelElement | null;
  if (label) label.htmlFor = input.id;

  row.appendChild(chipBox);
  row.appendChild(input);

  function commit(items: string[]): void {
    const cleaned = Array.from(new Set(items.map((s) => s.trim()).filter(Boolean)));
    if (cleaned.length === 0) {
      if (!required) doc.removeField(name);
      else doc.setField(name, []);
    } else {
      doc.setField(name, cleaned);
    }
    onChange();
    refresh();
  }

  function readChips(): string[] {
    const v = doc.getField(name);
    if (Array.isArray(v)) return v;
    if (typeof v === "string" && v) return [v];
    return [];
  }

  function refresh(): void {
    chipBox.innerHTML = "";
    for (const chip of readChips()) {
      const pill = document.createElement("span");
      pill.className = "attune-fm-chip";
      const text = document.createElement("span");
      text.textContent = chip;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "attune-fm-chip-remove";
      remove.textContent = "×";
      remove.title = `Remove ${chip}`;
      remove.addEventListener("click", () => {
        commit(readChips().filter((c) => c !== chip));
      });
      pill.appendChild(text);
      pill.appendChild(remove);
      if (onRename && (name === "tags" || name === "aliases")) {
        const field: RenamableField = name;
        pill.classList.add("attune-fm-chip-renamable");
        pill.title = `${chip} — right-click to rename`;
        pill.addEventListener("contextmenu", (ev) => {
          ev.preventDefault();
          onRename(field, chip);
        });
      }
      chipBox.appendChild(pill);
    }
  }

  function maybeCommitInput(): void {
    const raw = input.value.trim();
    if (!raw) return;
    commit([...readChips(), ...raw.split(",")]);
    input.value = "";
  }

  input.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" || ev.key === ",") {
      ev.preventDefault();
      maybeCommitInput();
    } else if (ev.key === "Backspace" && input.value === "") {
      const chips = readChips();
      if (chips.length > 0) {
        commit(chips.slice(0, -1));
      }
    }
  });
  input.addEventListener("blur", () => {
    if (input.value.trim()) maybeCommitInput();
  });

  refresh();
  return { refresh };
}

function renderUnknownFields(
  parent: HTMLElement,
  doc: TemplateDocument,
  knownKeys: ReadonlySet<string>,
): FieldRenderer {
  const section = document.createElement("section");
  section.className = "attune-fm-unknown";

  const heading = document.createElement("h4");
  heading.textContent = "Other fields";
  heading.className = "attune-fm-unknown-head";

  const list = document.createElement("dl");
  list.className = "attune-fm-unknown-list";

  parent.appendChild(section);
  section.appendChild(heading);
  section.appendChild(list);

  function refresh(): void {
    list.innerHTML = "";
    let any = false;
    for (const key of doc.getFieldOrder()) {
      if (knownKeys.has(key)) continue;
      any = true;
      const dt = document.createElement("dt");
      dt.textContent = key;
      const dd = document.createElement("dd");
      const v = doc.getField(key);
      if (Array.isArray(v)) dd.textContent = `[${v.join(", ")}]`;
      else dd.textContent = String(v ?? "");
      list.appendChild(dt);
      list.appendChild(dd);
    }
    section.hidden = !any;
  }

  refresh();
  return { refresh };
}

// -- Raw YAML toggle ---------------------------------------------------

function renderRawYamlPane(
  parent: HTMLElement,
  doc: TemplateDocument,
  onChange: () => void,
): FieldRenderer {
  const wrap = document.createElement("div");
  wrap.className = "attune-fm-rawyaml";
  const ta = document.createElement("textarea");
  ta.className = "attune-fm-input attune-fm-rawyaml-input";
  ta.rows = 14;
  ta.spellcheck = false;
  ta.id = "attune-fm-rawyaml";
  wrap.appendChild(ta);
  parent.appendChild(wrap);

  function readYaml(): string {
    // Reconstruct the frontmatter block from the doc's known fields
    // plus any unknown keys, in original order.
    const order = doc.getFieldOrder();
    const lines: string[] = [];
    for (const key of order) {
      const v = doc.getField(key);
      if (Array.isArray(v)) {
        lines.push(`${key}: [${v.join(", ")}]`);
      } else if (typeof v === "string") {
        lines.push(`${key}: ${v}`);
      }
    }
    return lines.join("\n");
  }

  ta.addEventListener("input", () => {
    // Round-trip the textarea contents through `setText` by injecting
    // them into a fake full-template string; let the model reparse.
    const fake = `---\n${ta.value}\n---\n${doc.getBody()}`;
    doc.setText(fake);
    onChange();
  });

  function refresh(): void {
    ta.value = readYaml();
  }
  refresh();
  return { refresh };
}

// -- Form host ---------------------------------------------------------

export function renderFrontmatterForm(parent: HTMLElement, bindings: FormBindings): FormHandle {
  const { doc, schema, onChange, onRename } = bindings;
  parent.innerHTML = "";
  parent.classList.add("attune-fm-form");

  const toolbar = document.createElement("div");
  toolbar.className = "attune-fm-toolbar";
  const rawBtn = document.createElement("button");
  rawBtn.type = "button";
  rawBtn.className = "attune-fm-toggle";
  rawBtn.textContent = "Raw YAML";
  rawBtn.setAttribute("aria-pressed", "false");
  toolbar.appendChild(rawBtn);
  parent.appendChild(toolbar);

  const formBody = document.createElement("div");
  formBody.className = "attune-fm-body";
  parent.appendChild(formBody);

  const required = new Set(schema.required ?? []);
  const renderers: FieldRenderer[] = [];

  function renderTyped(): void {
    formBody.innerHTML = "";
    renderers.length = 0;
    const known = new Set<string>();
    const props = schema.properties ?? {};
    for (const [name, prop] of Object.entries(props)) {
      known.add(name);
      let r: FieldRenderer;
      if (Array.isArray(prop.enum) && prop.enum.length > 0) {
        r = renderEnumField(formBody, doc, name, prop, required.has(name), onChange);
      } else if (isArrayProperty(prop)) {
        r = renderArrayField(formBody, doc, name, prop, required.has(name), onChange, onRename);
      } else {
        r = renderStringField(formBody, doc, name, prop, required.has(name), onChange);
      }
      renderers.push(r);
    }
    if (schema.additionalProperties !== false) {
      renderers.push(renderUnknownFields(formBody, doc, known));
    }
    // Seed values from the document so re-renders (e.g., after a Raw
    // YAML toggle) pick up the latest state.
    for (const r of renderers) r.refresh();
  }

  function renderRaw(): void {
    formBody.innerHTML = "";
    renderers.length = 0;
    renderers.push(renderRawYamlPane(formBody, doc, onChange));
  }

  let raw = false;
  rawBtn.addEventListener("click", () => {
    raw = !raw;
    rawBtn.setAttribute("aria-pressed", String(raw));
    rawBtn.classList.toggle("attune-fm-toggle-on", raw);
    if (raw) renderRaw();
    else renderTyped();
  });

  renderTyped();

  return {
    refresh() {
      for (const r of renderers) r.refresh();
    },
  };
}
