/**
 * Autocomplete extension for the template editor.
 *
 * Triggers in three contexts:
 *
 *   1. Inside ``[[…]]`` body refs   → kind=alias, prefix is the partial
 *      name between the opening ``[[`` and the cursor.
 *   2. After ``tags:`` in frontmatter → kind=tag, prefix is the partial
 *      token under the cursor (after the last comma or `[`).
 *   3. After ``aliases:`` in frontmatter → kind=alias, same shape as
 *      tags.
 *
 * Results are cached per ``(kind, prefix)`` for the lifetime of the
 * editor; the cache is intentionally simple (Map keyed by string) and
 * ignores TTL — the surrounding shell will call ``invalidateCache``
 * when a WS file-change event fires (wired in M3 task #20 onwards).
 */

import {
  type CompletionContext,
  type CompletionResult,
  autocompletion,
} from "@codemirror/autocomplete";
import type { EditorApi, AliasInfo, AutocompleteKind } from "./api";

export interface AutocompleteBindings {
  api: EditorApi;
  corpusId: string;
}

const FRONTMATTER_DELIM = "---";
const ALIAS_OPEN = /\[\[([^\[\]\n]*)$/;
const FRONTMATTER_LIST_KEY = /^(tags|aliases)\s*:\s*(.*)$/;
const TOKEN_TAIL = /[A-Za-z0-9._\-/]*$/;

interface CacheEntry {
  kind: AutocompleteKind;
  prefix: string;
  results: string[] | AliasInfo[];
}

export class AutocompleteCache {
  private readonly entries = new Map<string, CacheEntry>();

  key(kind: AutocompleteKind, prefix: string): string {
    return `${kind}|${prefix.toLowerCase()}`;
  }

  get(kind: AutocompleteKind, prefix: string): CacheEntry | undefined {
    return this.entries.get(this.key(kind, prefix));
  }

  set(entry: CacheEntry): void {
    this.entries.set(this.key(entry.kind, entry.prefix), entry);
  }

  clear(): void {
    this.entries.clear();
  }
}

interface FrontMatterRange {
  /** 0-indexed start line of the open `---` (inclusive). */
  open: number;
  /** 0-indexed line of the close `---` (inclusive). */
  close: number;
}

/** Locate the leading frontmatter range, if any.
 *
 * Treats an unterminated leading `---` block as in-frontmatter through
 * end-of-document — the user typing inside an under-construction
 * frontmatter still wants tag/alias completion to fire.
 */
function findFrontmatter(lines: readonly string[]): FrontMatterRange | null {
  if (lines[0] !== FRONTMATTER_DELIM) return null;
  for (let i = 1; i < lines.length; i += 1) {
    if (lines[i] === FRONTMATTER_DELIM) return { open: 0, close: i };
  }
  return { open: 0, close: lines.length };
}

interface CursorContext {
  kind: AutocompleteKind;
  prefix: string;
  /** Offset of the start of the prefix in the document. */
  from: number;
  /** Offset where insertion ends (cursor pos). */
  to: number;
}

/** Decide which autocomplete (if any) applies for the given cursor. */
export function inferContext(text: string, pos: number): CursorContext | null {
  // Walk backward for the alias `[[` body case first — independent of
  // frontmatter detection.
  const before = text.slice(Math.max(0, pos - 256), pos);
  const aliasMatch = ALIAS_OPEN.exec(before);
  if (aliasMatch) {
    const prefix = aliasMatch[1];
    return {
      kind: "alias",
      prefix,
      from: pos - prefix.length,
      to: pos,
    };
  }

  // Frontmatter `tags:` / `aliases:` case — only valid inside the
  // frontmatter block.
  const lines = text.split("\n");
  const fm = findFrontmatter(lines);
  if (!fm) return null;

  // Resolve the cursor's line index.
  let cursor = 0;
  let lineIdx = 0;
  for (let i = 0; i < lines.length; i += 1) {
    const lineEnd = cursor + lines[i].length;
    if (pos <= lineEnd) {
      lineIdx = i;
      break;
    }
    cursor = lineEnd + 1; // include consumed `\n`
  }
  if (lineIdx <= fm.open || lineIdx >= fm.close) return null;

  const lineText = lines[lineIdx];
  const m = FRONTMATTER_LIST_KEY.exec(lineText);
  if (!m) return null;

  const kind: AutocompleteKind = m[1] === "tags" ? "tag" : "alias";
  // Compute the column of the cursor on this line.
  const lineStart = cursor;
  const colOnLine = pos - lineStart;
  const before2 = lineText.slice(0, colOnLine);
  // The "values" portion of the line starts after `key:`. Find that
  // boundary so we don't scan into the key itself.
  const keyEnd = lineText.indexOf(":") + 1;
  if (colOnLine < keyEnd) return null;

  // Identify the start of the current token: the position after the
  // most recent `,` or `[` (or `:` if no separator yet). Trailing
  // whitespace is trimmed so the prefix is just the token.
  let separator = -1;
  for (let i = colOnLine - 1; i >= keyEnd; i -= 1) {
    const c = before2[i];
    if (c === "," || c === "[") {
      separator = i;
      break;
    }
  }
  const tokenStart = (separator >= 0 ? separator : keyEnd - 1) + 1;
  const tokenSegment = before2.slice(tokenStart);
  // Skip whitespace at the segment's leading edge.
  const wsStripped = tokenSegment.replace(/^\s+/, "");
  const tokenColStart = tokenStart + (tokenSegment.length - wsStripped.length);
  const tokenMatch = TOKEN_TAIL.exec(wsStripped);
  const prefix = tokenMatch ? tokenMatch[0] : "";

  return {
    kind,
    prefix,
    from: lineStart + tokenColStart,
    to: pos,
  };
}

function toCompletionResult(
  ctx: CursorContext,
  results: string[] | AliasInfo[],
): CompletionResult {
  const options = (results as Array<string | AliasInfo>).map((r) => {
    if (typeof r === "string") {
      return { label: r, type: ctx.kind === "tag" ? "keyword" : "variable" };
    }
    return {
      label: r.alias,
      detail: r.template_name,
      info: r.template_path,
      type: "variable",
    };
  });
  return {
    from: ctx.from,
    to: ctx.to,
    options,
    validFor: /[A-Za-z0-9._\-/]*$/,
  };
}

export function attuneCompletions(bindings: AutocompleteBindings) {
  const cache = new AutocompleteCache();

  async function source(cx: CompletionContext): Promise<CompletionResult | null> {
    const text = cx.state.doc.toString();
    const ctx = inferContext(text, cx.pos);
    if (!ctx) return null;
    if (!cx.explicit && ctx.prefix.length === 0) return null;

    const cached = cache.get(ctx.kind, ctx.prefix);
    if (cached) return toCompletionResult(ctx, cached.results);

    try {
      const results = await bindings.api.autocomplete(
        bindings.corpusId,
        ctx.kind,
        ctx.prefix,
      );
      cache.set({ kind: ctx.kind, prefix: ctx.prefix, results });
      return toCompletionResult(ctx, results);
    } catch {
      return null;
    }
  }

  return {
    extension: autocompletion({
      override: [source],
      activateOnTyping: true,
    }),
    invalidateCache: () => cache.clear(),
  };
}
