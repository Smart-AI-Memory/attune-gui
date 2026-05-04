/**
 * Document model for the template editor.
 *
 * A template is a Markdown file with an optional YAML frontmatter block.
 * The model holds both representations and round-trips between them so
 * the frontmatter form and the editor pane share a single source of
 * truth — editing in either view produces the same on-disk text.
 *
 * The YAML parser/serializer is intentionally minimal: it understands
 * the subset of frontmatter attune templates use today (string scalars
 * and string arrays). Full schema-driven editing (with type coercion)
 * lands in task #16; this module is what that form will sit on top of.
 */

const FRONTMATTER_DELIM = "---";

export interface FrontMatterFields {
  /** Ordered key insertion to preserve round-trip order on serialize. */
  readonly order: readonly string[];
  /** Either a scalar string or a string array (unknown shapes -> string). */
  readonly values: Readonly<Record<string, string | string[]>>;
  /** Verbatim original text — preserved when no field-level edits were made. */
  readonly originalText: string;
}

export interface SplitResult {
  frontmatterText: string;
  body: string;
  /** True when the document started with a `---` frontmatter block. */
  hasFrontMatter: boolean;
}

const TOP_LEVEL_KEY_RE = /^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$/;

/** Split a template into (frontmatter, body). Empty fm if no block. */
export function splitFrontMatter(text: string): SplitResult {
  if (!text.startsWith(`${FRONTMATTER_DELIM}\n`) && text !== FRONTMATTER_DELIM) {
    return { frontmatterText: "", body: text, hasFrontMatter: false };
  }
  // Skip the opening `---\n` (4 chars).
  const after = text.slice(FRONTMATTER_DELIM.length + 1);
  // Find the closing `---` on its own line.
  const closer = after.search(/(^|\n)---(\n|$)/);
  if (closer < 0) {
    return { frontmatterText: "", body: text, hasFrontMatter: false };
  }
  const fm = closer === 0 ? "" : after.slice(0, closer + (after[closer] === "\n" ? 1 : 0));
  // Position past the closing delimiter.
  let bodyStart = closer + (after[closer] === "\n" ? 1 : 0) + FRONTMATTER_DELIM.length;
  if (after[bodyStart] === "\n") bodyStart += 1;
  return {
    frontmatterText: fm.replace(/\n$/, ""),
    body: after.slice(bodyStart),
    hasFrontMatter: true,
  };
}

/** Parse a tiny subset of YAML — string scalars and `[a, b]` flow arrays. */
export function parseFrontMatter(text: string): FrontMatterFields {
  const lines = text.split("\n");
  const order: string[] = [];
  const values: Record<string, string | string[]> = {};

  for (const line of lines) {
    if (!line.trim() || line.trimStart().startsWith("#")) continue;
    const m = TOP_LEVEL_KEY_RE.exec(line);
    if (!m) continue;
    const key = m[1];
    const raw = m[2].trim();
    if (order.includes(key)) continue;
    order.push(key);

    if (raw.startsWith("[") && raw.endsWith("]")) {
      // Flow array: [a, b, "c d"]
      const inner = raw.slice(1, -1).trim();
      values[key] = inner ? splitFlowArray(inner) : [];
    } else if (raw.startsWith('"') && raw.endsWith('"')) {
      values[key] = raw.slice(1, -1).replace(/\\"/g, '"');
    } else if (raw.startsWith("'") && raw.endsWith("'")) {
      values[key] = raw.slice(1, -1).replace(/''/g, "'");
    } else {
      values[key] = raw;
    }
  }

  return { order, values, originalText: text };
}

function splitFlowArray(inner: string): string[] {
  // Splits on commas that are outside of quoted strings.
  const out: string[] = [];
  let buf = "";
  let quote: '"' | "'" | null = null;
  for (let i = 0; i < inner.length; i += 1) {
    const c = inner[i];
    if (quote) {
      if (c === quote) {
        quote = null;
      } else {
        buf += c;
      }
    } else if (c === '"' || c === "'") {
      quote = c;
    } else if (c === ",") {
      out.push(buf.trim());
      buf = "";
    } else {
      buf += c;
    }
  }
  if (buf.trim()) out.push(buf.trim());
  return out;
}

/** Re-emit fields as YAML, preserving key order and array compactness. */
export function serializeFrontMatter(fields: FrontMatterFields): string {
  const lines: string[] = [];
  for (const key of fields.order) {
    const v = fields.values[key];
    if (Array.isArray(v)) {
      const items = v.map(quoteIfNeeded).join(", ");
      lines.push(`${key}: [${items}]`);
    } else if (v !== undefined) {
      lines.push(`${key}: ${quoteIfNeeded(v)}`);
    }
  }
  return lines.join("\n");
}

function quoteIfNeeded(value: string): string {
  if (value === "") return '""';
  if (/^[\w./-]+$/.test(value)) return value;
  // Escape backslashes, then quotes.
  return `"${value.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
}

/** Combine frontmatter and body back into a full template text.
 *
 * ``body`` is expected to come from ``splitFrontMatter`` — its leading
 * newline (the blank line between fm and body in the original source)
 * is preserved verbatim so round-trips are byte-identical when no
 * field-level edits were made.
 */
export function combine(frontmatterText: string, body: string): string {
  if (!frontmatterText.trim()) return body;
  const fm = frontmatterText.endsWith("\n") ? frontmatterText : `${frontmatterText}\n`;
  return `${FRONTMATTER_DELIM}\n${fm}${FRONTMATTER_DELIM}\n${body}`;
}

/**
 * Single-source-of-truth document.
 *
 * Edits flow in three ways:
 *   1. ``setText(t)``      — full editor pane edit; reparses frontmatter.
 *   2. ``setField(k, v)``  — form edit; rewrites the frontmatter block.
 *   3. ``setBody(b)``      — body-only edit (the editor never calls this
 *                            directly — it lives here for tests).
 *
 * After any edit ``getText()`` returns the canonical full text.
 */
export class TemplateDocument {
  private fields: FrontMatterFields;
  private body: string;
  private hasFrontMatter: boolean;

  constructor(text: string) {
    const split = splitFrontMatter(text);
    this.fields = parseFrontMatter(split.frontmatterText);
    this.body = split.body;
    this.hasFrontMatter = split.hasFrontMatter;
  }

  static empty(): TemplateDocument {
    return new TemplateDocument("");
  }

  getText(): string {
    if (!this.hasFrontMatter && this.fields.order.length === 0) return this.body;
    const fmText =
      this.fields.order.length === 0 ? this.fields.originalText : serializeFrontMatter(this.fields);
    return combine(fmText, this.body);
  }

  setText(text: string): void {
    const split = splitFrontMatter(text);
    this.fields = parseFrontMatter(split.frontmatterText);
    this.body = split.body;
    this.hasFrontMatter = split.hasFrontMatter;
  }

  getField(key: string): string | string[] | undefined {
    return this.fields.values[key];
  }

  setField(key: string, value: string | string[]): void {
    const order = this.fields.order.includes(key)
      ? this.fields.order
      : [...this.fields.order, key];
    this.fields = {
      order,
      values: { ...this.fields.values, [key]: value },
      originalText: this.fields.originalText,
    };
    this.hasFrontMatter = true;
  }

  removeField(key: string): void {
    if (!this.fields.order.includes(key)) return;
    const { [key]: _removed, ...rest } = this.fields.values;
    void _removed;
    this.fields = {
      order: this.fields.order.filter((k) => k !== key),
      values: rest,
      originalText: this.fields.originalText,
    };
  }

  getFieldOrder(): readonly string[] {
    return this.fields.order;
  }

  getBody(): string {
    return this.body;
  }

  setBody(body: string): void {
    this.body = body;
  }
}
