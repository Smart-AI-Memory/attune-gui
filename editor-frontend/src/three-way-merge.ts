/**
 * Three-way merge primitive for conflict mode.
 *
 * Wraps `node-diff3`'s `diff3Merge` into the shape the conflict UI
 * wants: a flat list of regions, each either auto-merged (the
 * editor accepted one side cleanly) or a conflict that needs a
 * user decision.
 *
 * Region orientation: `o` is the common base (the file as the
 * editor first loaded it), `a` is the *disk* version (what's on
 * disk now after an external edit), and `b` is the *editor*
 * version (what the user is currently typing). This mirrors how a
 * VCS calls them — local vs incoming — but with editor-specific
 * names so the UI labels are unambiguous.
 *
 * Resolution model: the user picks one of `disk`, `editor`, or
 * `both` for each conflict region. `applyResolutions` walks the
 * regions in order and emits the final text.
 */

import { diff3Merge } from "node-diff3";

export type ConflictChoice = "disk" | "editor" | "both";

export type MergeRegion =
  | { kind: "auto"; lines: string[] }
  | {
      kind: "conflict";
      diskLines: string[];
      editorLines: string[];
      baseLines: string[];
      /** Stable id within a single merge result; used as a UI key. */
      id: string;
    };

export interface MergeResult {
  regions: MergeRegion[];
  /** True if any region is a conflict. */
  hasConflict: boolean;
}

const NEWLINE = /\r?\n/;

/**
 * Compute a 3-way merge between the on-disk version (`disk`), the
 * common base (`base`), and the in-editor draft (`editor`).
 *
 * The function is line-oriented. Trailing newlines round-trip: if
 * any of the three inputs ends with `\n`, the joined output does
 * too (the more common case wins for ties; absence loses).
 */
export function threeWayMerge(
  disk: string,
  base: string,
  editor: string,
): MergeResult {
  const diskLines = splitLines(disk);
  const baseLines = splitLines(base);
  const editorLines = splitLines(editor);

  // Note the argument order: diff3Merge(a, o, b) where a = "mine",
  // o = "original", b = "theirs". We map a → disk, b → editor so
  // the conflict regions read disk-on-the-left, editor-on-the-right.
  const raw = diff3Merge(diskLines, baseLines, editorLines, {
    excludeFalseConflicts: true,
  });

  const regions: MergeRegion[] = [];
  let conflictCount = 0;

  for (const block of raw) {
    if (block.ok !== undefined) {
      if (block.ok.length === 0) continue;
      regions.push({ kind: "auto", lines: block.ok });
    } else if (block.conflict !== undefined) {
      const c = block.conflict;
      regions.push({
        kind: "conflict",
        diskLines: c.a,
        editorLines: c.b,
        baseLines: c.o,
        id: `c${conflictCount++}`,
      });
    }
  }

  return {
    regions,
    hasConflict: conflictCount > 0,
  };
}

/**
 * Apply a per-conflict resolution map to a set of merge regions.
 *
 * Missing entries default to `editor` (preserving the user's typing
 * is the safer default if the UI is wired up incorrectly).
 */
export function applyResolutions(
  regions: readonly MergeRegion[],
  resolutions: Readonly<Record<string, ConflictChoice>>,
  trailingNewline: boolean,
): string {
  const out: string[] = [];
  for (const region of regions) {
    if (region.kind === "auto") {
      out.push(...region.lines);
    } else {
      const choice = resolutions[region.id] ?? "editor";
      if (choice === "disk") {
        out.push(...region.diskLines);
      } else if (choice === "editor") {
        out.push(...region.editorLines);
      } else {
        // "both": disk first, then editor. The order matches what a
        // VCS conflict marker tradition does (local first, incoming
        // second) but without the marker text — the user is committing
        // to a real text result here.
        out.push(...region.diskLines);
        out.push(...region.editorLines);
      }
    }
  }
  return out.join("\n") + (trailingNewline ? "\n" : "");
}

/**
 * Heuristic for the trailing-newline argument to `applyResolutions`.
 *
 * Defaults to whatever the editor draft has (the user's most recent
 * intent), falling back to disk, falling back to base. Mirrors how
 * most editors treat the trailing-newline question — sticky to the
 * actively-edited buffer.
 */
export function preferredTrailingNewline(
  disk: string,
  base: string,
  editor: string,
): boolean {
  if (editor.length > 0) return editor.endsWith("\n");
  if (disk.length > 0) return disk.endsWith("\n");
  return base.endsWith("\n");
}

function splitLines(text: string): string[] {
  if (text === "") return [];
  // Drop the trailing empty element produced when text ends in \n;
  // the trailing-newline decision is reattached at join time.
  const parts = text.split(NEWLINE);
  if (parts[parts.length - 1] === "") parts.pop();
  return parts;
}

