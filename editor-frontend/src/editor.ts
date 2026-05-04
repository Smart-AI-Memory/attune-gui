/**
 * CodeMirror 6 mount for the template editor.
 *
 * Composes:
 *   - basicSetup (line numbers, history, search, etc.)
 *   - markdown() with our Attune extension (front-matter, depth, alias)
 *   - diff gutter relative to the base text
 *   - an update listener that pushes edits back into the document model
 */

import { EditorState, type Extension } from "@codemirror/state";
import { EditorView, keymap } from "@codemirror/view";
import { defaultKeymap, history, historyKeymap } from "@codemirror/commands";
import { markdown } from "@codemirror/lang-markdown";
import { syntaxHighlighting, defaultHighlightStyle, foldGutter } from "@codemirror/language";

import { attuneMarkdownExtension } from "./grammar/markdown-extension";
import { diffGutter, updateDiffMarkers } from "./diff-gutter";

export interface MountOptions {
  parent: HTMLElement;
  initialText: string;
  /** Base text used to compute diff-gutter markers. */
  baseText: string;
  /** Called after each user edit (debouncing is the caller's job). */
  onChange?: (text: string) => void;
}

export interface MountedEditor {
  view: EditorView;
  /** Update the diff-gutter base (call after a successful save). */
  setBase(text: string): void;
  /** Replace the editor contents (call when reloading from disk). */
  setText(text: string): void;
  destroy(): void;
}

export function mountEditor(opts: MountOptions): MountedEditor {
  let base = opts.baseText;

  const extensions: Extension[] = [
    history(),
    keymap.of([...defaultKeymap, ...historyKeymap]),
    markdown({ extensions: [attuneMarkdownExtension] }),
    syntaxHighlighting(defaultHighlightStyle),
    foldGutter(),
    diffGutter(),
    EditorView.updateListener.of((update) => {
      if (update.docChanged) {
        updateDiffMarkers(update.view, base);
        if (opts.onChange) {
          opts.onChange(update.state.doc.toString());
        }
      }
    }),
    EditorView.theme({
      "&": { height: "100%" },
      ".cm-scroller": { fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" },
      ".attune-diff-gutter": { width: "1.4em", textAlign: "center" },
      ".attune-diff-added": { color: "#22863a" },
      ".attune-diff-modified": { color: "#b08800" },
      ".attune-diff-removed": { color: "#b31d28" },
    }),
  ];

  const view = new EditorView({
    state: EditorState.create({ doc: opts.initialText, extensions }),
    parent: opts.parent,
  });

  // Seed gutter on first mount so an unedited doc shows zero markers.
  updateDiffMarkers(view, base);

  return {
    view,
    setBase(text: string) {
      base = text;
      updateDiffMarkers(view, base);
    },
    setText(text: string) {
      view.dispatch({
        changes: { from: 0, to: view.state.doc.length, insert: text },
      });
    },
    destroy() {
      view.destroy();
    },
  };
}
