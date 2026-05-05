// @vitest-environment happy-dom

import { describe, it, expect, beforeEach } from "vitest";
import {
  setAdvisories,
  GENERATED_CORPUS_MESSAGE,
  DUPLICATE_SESSION_MESSAGE,
} from "./advisory-banner";

let host: HTMLElement;

beforeEach(() => {
  document.body.innerHTML = "";
  host = document.createElement("div");
  document.body.appendChild(host);
});

describe("setAdvisories", () => {
  it("hides the strip when there are no advisories", () => {
    setAdvisories(host, []);
    expect(host.hidden).toBe(true);
    expect(host.children.length).toBe(0);
  });

  it("renders a generated-corpus advisory with the canonical copy", () => {
    setAdvisories(host, [{ kind: "generated", message: GENERATED_CORPUS_MESSAGE }]);
    expect(host.hidden).toBe(false);
    const row = host.querySelector(".attune-advisory-generated");
    expect(row).toBeTruthy();
    expect(row?.textContent).toContain("regenerated");
    expect(row?.textContent).toContain("overwritten");
  });

  it("renders a duplicate-session advisory with the canonical copy", () => {
    setAdvisories(host, [
      { kind: "duplicate_session", message: DUPLICATE_SESSION_MESSAGE },
    ]);
    const row = host.querySelector(".attune-advisory-duplicate_session");
    expect(row).toBeTruthy();
    expect(row?.textContent).toContain("Another tab");
    expect(row?.textContent).toContain("read-only");
  });

  it("stacks both advisories in document order", () => {
    setAdvisories(host, [
      { kind: "generated", message: GENERATED_CORPUS_MESSAGE },
      { kind: "duplicate_session", message: DUPLICATE_SESSION_MESSAGE },
    ]);
    const rows = [...host.querySelectorAll(".attune-advisory")];
    expect(rows).toHaveLength(2);
    expect(rows[0].classList.contains("attune-advisory-generated")).toBe(true);
    expect(rows[1].classList.contains("attune-advisory-duplicate_session")).toBe(true);
  });

  it("replaces previous advisories on each call (no stale rows)", () => {
    setAdvisories(host, [{ kind: "generated", message: "old" }]);
    setAdvisories(host, [{ kind: "duplicate_session", message: "new" }]);
    const rows = [...host.querySelectorAll(".attune-advisory")];
    expect(rows).toHaveLength(1);
    expect(rows[0].textContent).toContain("new");
  });

  it("toggles `hidden` back when called with an empty array", () => {
    setAdvisories(host, [{ kind: "generated", message: "x" }]);
    expect(host.hidden).toBe(false);
    setAdvisories(host, []);
    expect(host.hidden).toBe(true);
  });
});
