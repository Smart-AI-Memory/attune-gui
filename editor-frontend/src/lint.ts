/**
 * Lint extension for the template editor.
 *
 * Two layers:
 *
 *   1. Local fast-path: cheap structural checks done in the browser
 *      (e.g., unterminated frontmatter, invalid YAML at the top level).
 *      No server roundtrip; runs synchronously on every linter pass.
 *   2. Server: ``POST /api/corpus/<id>/lint`` returns the authoritative
 *      diagnostic list (broken aliases, depth-sequence issues, schema
 *      violations). Debounced 300 ms; pending requests abort when a new
 *      edit lands.
 *
 * Both layers emit ``@codemirror/lint`` ``Diagnostic`` objects so the
 * editor surface (squiggle + sidebar) stays uniform.
 */

import type { EditorView } from "@codemirror/view";
import { type Diagnostic, linter, type LintSource } from "@codemirror/lint";
import type { EditorApi, ServerDiagnostic, DiagnosticSeverity } from "./api";

export interface LintBindings {
  api: EditorApi;
  corpusId: string;
  relPath: string;
  /** Called whenever a fresh diagnostic list is available. */
  onDiagnostics?: (diagnostics: Diagnostic[]) => void;
}

const DEBOUNCE_MS = 300;
const FRONTMATTER_DELIM = "---";

interface LinePos {
  /** Character offset of the start of the 1-indexed ``line``. */
  start: number;
  /** Character offset of the end of the line (exclusive of newline). */
  end: number;
  length: number;
}

function lineOffsets(text: string): LinePos[] {
  const out: LinePos[] = [];
  let cursor = 0;
  for (const raw of text.split("\n")) {
    out.push({ start: cursor, end: cursor + raw.length, length: raw.length });
    cursor += raw.length + 1; // include the consumed `\n`
  }
  return out;
}

/** Convert a server (1-indexed line/col) range into CM (0-indexed offset). */
function toRange(
  text: string,
  diag: ServerDiagnostic,
): { from: number; to: number } | null {
  // Empty document: nothing for CM to attach a diagnostic to. Drop
  // the diagnostic rather than synthesize a 0..1 range CM will reject.
  if (text.length === 0) return null;

  const lines = lineOffsets(text);
  const lineIdx = diag.line - 1;
  const endIdx = diag.end_line - 1;
  if (lineIdx < 0 || lineIdx >= lines.length) return null;

  const startLine = lines[lineIdx];
  const colOffset = Math.max(0, Math.min(startLine.length, diag.col - 1));
  let from = startLine.start + colOffset;

  let to: number;
  if (endIdx < 0 || endIdx >= lines.length) {
    to = startLine.end;
  } else {
    const endLine = lines[endIdx];
    const endCol = Math.max(0, Math.min(endLine.length, diag.end_col - 1));
    to = endLine.start + endCol;
  }
  if (to < from) to = from;
  // Ensure the range is non-empty so CM can render a squiggle.
  if (from === to) {
    if (from < text.length) to = from + 1;
    else from = Math.max(0, from - 1);
  }
  // Final clamp so neither bound exceeds doc length.
  from = Math.min(from, text.length);
  to = Math.min(to, text.length);
  return { from, to };
}

function severityToCmSeverity(s: DiagnosticSeverity): Diagnostic["severity"] {
  // CM's severities: hint | info | warning | error
  return s === "error" ? "error" : s === "warning" ? "warning" : "info";
}

/** Local fast-path: catch unterminated frontmatter so the user sees a
 * diagnostic immediately even when the server is slow or unreachable. */
export function localDiagnostics(text: string): Diagnostic[] {
  const out: Diagnostic[] = [];
  if (!text.startsWith(`${FRONTMATTER_DELIM}\n`) && text !== FRONTMATTER_DELIM) {
    return out;
  }
  const after = text.slice(FRONTMATTER_DELIM.length + 1);
  const closer = after.search(/(^|\n)---(\n|$)/);
  if (closer < 0) {
    out.push({
      from: 0,
      to: Math.min(text.length, FRONTMATTER_DELIM.length),
      severity: "error",
      source: "attune-local",
      message: "Unterminated frontmatter — missing closing `---`.",
    });
  }
  return out;
}

interface DebounceState {
  timer: ReturnType<typeof setTimeout> | null;
  abort: AbortController | null;
}

/**
 * Build the lint extension.
 *
 * The returned extension installs CodeMirror's standard ``linter`` with
 * a debounced async source that runs both layers above, then unions the
 * results before returning them.
 */
export function attuneLinter(bindings: LintBindings) {
  const state: DebounceState = { timer: null, abort: null };

  const source: LintSource = (view: EditorView): Promise<Diagnostic[]> => {
    if (state.timer) clearTimeout(state.timer);
    if (state.abort) state.abort.abort();

    return new Promise((resolve) => {
      state.timer = setTimeout(async () => {
        const text = view.state.doc.toString();
        const local = localDiagnostics(text);

        const ctrl = new AbortController();
        state.abort = ctrl;
        let serverDiags: ServerDiagnostic[] = [];
        try {
          serverDiags = await bindings.api.lint(
            bindings.corpusId,
            { path: bindings.relPath, text },
            ctrl.signal,
          );
        } catch (err) {
          if (ctrl.signal.aborted) {
            // Superseded by a newer request — surface what we have.
          } else {
            // Network or 5xx: surface a single info diagnostic so the
            // user knows the server lint isn't running, but don't
            // block local fast-path diagnostics.
            local.push({
              from: 0,
              to: 1,
              severity: "info",
              source: "attune-server",
              message: `Server lint unavailable: ${(err as Error).message}`,
            });
          }
        }

        const fromServer: Diagnostic[] = [];
        for (const d of serverDiags) {
          const range = toRange(text, d);
          if (!range) continue;
          fromServer.push({
            from: range.from,
            to: range.to,
            severity: severityToCmSeverity(d.severity),
            message: d.message,
            source: `attune:${d.code}`,
          });
        }

        const all = [...local, ...fromServer];
        bindings.onDiagnostics?.(all);
        resolve(all);
      }, DEBOUNCE_MS);
    });
  };

  return linter(source, { delay: 0 });
}
