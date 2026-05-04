/**
 * Template editor entry point.
 *
 * Task #13 (M3) ships only the build pipeline. This module is a
 * placeholder that proves the bundle loads — task #15 replaces it
 * with the real CodeMirror mount + document model.
 */

import "./style.css";

const MOUNT_ID = "attune-editor-root";

function mount(): void {
  const root = document.getElementById(MOUNT_ID);
  if (!root) return;
  root.classList.add("attune-editor-bootstrapped");
  root.textContent = "Attune template editor — bundle loaded.";
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", mount, { once: true });
} else {
  mount();
}
