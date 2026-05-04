/**
 * Diagnostics strip.
 *
 * Renders an inline list of diagnostics under the editor pane.
 * Clicking an entry jumps the editor to the source line.
 *
 * The strip stays purely a sink — the lint extension is the source.
 * On every fresh diagnostic batch the caller invokes ``setDiagnostics``
 * and the strip re-renders.
 */

import type { EditorView } from "@codemirror/view";
import type { Diagnostic } from "@codemirror/lint";

export interface DiagnosticsStripBindings {
  view: EditorView;
}

export interface DiagnosticsStrip {
  setDiagnostics(diagnostics: Diagnostic[]): void;
}

const SEVERITY_LABEL: Record<NonNullable<Diagnostic["severity"]>, string> = {
  error: "✖",
  warning: "⚠",
  info: "ⓘ",
  hint: "ⓘ",
};

export function renderDiagnosticsStrip(
  parent: HTMLElement,
  bindings: DiagnosticsStripBindings,
): DiagnosticsStrip {
  parent.classList.add("attune-editor-diagnostics");
  parent.innerHTML = "";

  const summary = document.createElement("div");
  summary.className = "attune-diag-summary";
  parent.appendChild(summary);

  const list = document.createElement("ul");
  list.className = "attune-diag-list";
  parent.appendChild(list);

  function setDiagnostics(diags: Diagnostic[]): void {
    const counts = { error: 0, warning: 0, info: 0, hint: 0 };
    for (const d of diags) counts[d.severity ?? "info"] += 1;
    summary.textContent = diags.length
      ? `${counts.error} error · ${counts.warning} warning · ${counts.info + counts.hint} info`
      : "no diagnostics";

    list.innerHTML = "";
    for (const d of diags) {
      const item = document.createElement("li");
      item.className = `attune-diag attune-diag-${d.severity ?? "info"}`;
      item.tabIndex = 0;

      const icon = document.createElement("span");
      icon.className = "attune-diag-icon";
      icon.textContent = SEVERITY_LABEL[d.severity ?? "info"];

      const lineLabel = document.createElement("span");
      lineLabel.className = "attune-diag-line";
      const line = bindings.view.state.doc.lineAt(d.from).number;
      lineLabel.textContent = `line ${line}`;

      const message = document.createElement("span");
      message.className = "attune-diag-msg";
      message.textContent = d.message;

      const source = document.createElement("span");
      source.className = "attune-diag-source";
      source.textContent = d.source ?? "";

      item.appendChild(icon);
      item.appendChild(lineLabel);
      item.appendChild(message);
      if (d.source) item.appendChild(source);

      const jump = (): void => {
        bindings.view.dispatch({
          selection: { anchor: d.from, head: d.to },
          scrollIntoView: true,
        });
        bindings.view.focus();
      };
      item.addEventListener("click", jump);
      item.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          jump();
        }
      });
      list.appendChild(item);
    }
  }

  // Initial empty render so the summary line exists before lint runs.
  setDiagnostics([]);
  return { setDiagnostics };
}
