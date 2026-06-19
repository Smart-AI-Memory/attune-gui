// @vitest-environment happy-dom

import { describe, it, expect, beforeEach, vi } from "vitest";
import { mountProvenancePanel } from "./provenance-panel";
import type { EditorApi, Provenance } from "./api";

let host: HTMLElement;

beforeEach(() => {
  document.body.innerHTML = "";
  host = document.createElement("div");
  document.body.appendChild(host);
});

function fakeApi(prov: Partial<Provenance>): EditorApi {
  const full: Provenance = {
    bound: true,
    status: "fresh",
    feature: "auth",
    stored_hash: "abc",
    current_hash: "abc",
    depth: "concept",
    generated_at: "2026-01-01",
    source_files: ["src/auth/login.py"],
    source_globs: ["src/auth/**"],
    can_regenerate: false,
    reason: null,
    ...prov,
  };
  return {
    getProvenance: vi.fn().mockResolvedValue(full),
    regenerateTemplate: vi.fn(),
    getJob: vi.fn(),
  } as unknown as EditorApi;
}

async function flush(): Promise<void> {
  // Let the panel's async refresh() resolve.
  await Promise.resolve();
  await Promise.resolve();
}

describe("mountProvenancePanel", () => {
  it("renders a green fresh row with no regenerate button", async () => {
    mountProvenancePanel({ host, api: fakeApi({ status: "fresh" }), corpusId: "c", relPath: "t.md" });
    await flush();
    expect(host.querySelector(".attune-prov-dot-fresh")).toBeTruthy();
    expect(host.querySelector(".attune-prov-label")?.textContent).toContain("matches source");
    const btn = host.querySelector(".attune-prov-regen") as HTMLButtonElement;
    expect(btn.hidden).toBe(true);
  });

  it("renders an amber stale row with an enabled regenerate button", async () => {
    mountProvenancePanel({
      host,
      api: fakeApi({ status: "stale", can_regenerate: true }),
      corpusId: "c",
      relPath: "t.md",
    });
    await flush();
    expect(host.querySelector(".attune-prov-dot-stale")).toBeTruthy();
    const btn = host.querySelector(".attune-prov-regen") as HTMLButtonElement;
    expect(btn.hidden).toBe(false);
    expect(btn.disabled).toBe(false);
  });

  it("renders a grey unbound row, no button, reason as tooltip", async () => {
    mountProvenancePanel({
      host,
      api: fakeApi({ status: "unbound", bound: false, can_regenerate: false, reason: "hand-authored" }),
      corpusId: "c",
      relPath: "t.md",
    });
    await flush();
    expect(host.querySelector(".attune-prov-dot-unbound")).toBeTruthy();
    const label = host.querySelector(".attune-prov-label") as HTMLElement;
    expect(label.title).toBe("hand-authored");
    expect((host.querySelector(".attune-prov-regen") as HTMLButtonElement).hidden).toBe(true);
  });

  it("renders a red sources-missing row with the button disabled", async () => {
    mountProvenancePanel({
      host,
      api: fakeApi({ status: "sources_missing", can_regenerate: false }),
      corpusId: "c",
      relPath: "t.md",
    });
    await flush();
    expect(host.querySelector(".attune-prov-dot-sources_missing")).toBeTruthy();
    expect((host.querySelector(".attune-prov-regen") as HTMLButtonElement).hidden).toBe(true);
  });
});
