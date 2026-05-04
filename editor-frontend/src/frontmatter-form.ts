/**
 * Minimal frontmatter form sidebar.
 *
 * v1: hand-rolled inputs for the well-known fields (``type``, ``name``,
 * ``tags``, ``aliases``, ``summary``). Schema-driven rendering — the
 * thing that decides which fields exist by reading
 * ``template_schema.json`` — lands in task #16.
 *
 * The form binds to a ``TemplateDocument``: editing in the form calls
 * ``setField`` on the doc; the caller is expected to push the resulting
 * ``getText()`` back into CodeMirror (or vice versa).
 */

import type { TemplateDocument } from "./document-model";

export interface FormBindings {
  doc: TemplateDocument;
  /** Called after every form edit so the caller can reflect into CM. */
  onChange: () => void;
}

const KNOWN_FIELDS: Array<{
  key: string;
  label: string;
  kind: "text" | "textarea" | "list";
}> = [
  { key: "type", label: "type", kind: "text" },
  { key: "name", label: "name", kind: "text" },
  { key: "tags", label: "tags", kind: "list" },
  { key: "aliases", label: "aliases", kind: "list" },
  { key: "summary", label: "summary", kind: "textarea" },
];

export function renderFrontmatterForm(parent: HTMLElement, bindings: FormBindings): {
  refresh(): void;
} {
  const { doc, onChange } = bindings;
  parent.innerHTML = "";
  parent.classList.add("attune-fm-form");

  const inputs = new Map<string, HTMLInputElement | HTMLTextAreaElement>();

  for (const field of KNOWN_FIELDS) {
    const row = document.createElement("div");
    row.className = "attune-fm-row";

    const label = document.createElement("label");
    label.className = "attune-fm-label";
    label.textContent = field.label;

    let input: HTMLInputElement | HTMLTextAreaElement;
    if (field.kind === "textarea") {
      input = document.createElement("textarea");
      input.rows = 3;
    } else {
      input = document.createElement("input");
      input.type = "text";
      if (field.kind === "list") {
        input.placeholder = "comma-separated";
      }
    }
    input.id = `attune-fm-${field.key}`;
    input.className = "attune-fm-input";
    label.htmlFor = input.id;
    inputs.set(field.key, input);

    input.addEventListener("input", () => {
      const raw = input.value;
      if (field.kind === "list") {
        const items = raw
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
        if (items.length === 0) {
          doc.removeField(field.key);
        } else {
          doc.setField(field.key, items);
        }
      } else if (raw === "" && doc.getField(field.key) !== undefined) {
        doc.removeField(field.key);
      } else {
        doc.setField(field.key, raw);
      }
      onChange();
    });

    row.appendChild(label);
    row.appendChild(input);
    parent.appendChild(row);
  }

  function refresh(): void {
    for (const field of KNOWN_FIELDS) {
      const input = inputs.get(field.key);
      if (!input) continue;
      const value = doc.getField(field.key);
      if (Array.isArray(value)) {
        input.value = value.join(", ");
      } else if (typeof value === "string") {
        input.value = value;
      } else {
        input.value = "";
      }
    }
  }

  refresh();
  return { refresh };
}
