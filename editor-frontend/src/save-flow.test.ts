import { describe, it, expect } from "vitest";
import { applyAcceptedHunks, parseHunkHeader, saveButtonLabel } from "./save-flow";
import type { Hunk } from "./api";

describe("parseHunkHeader", () => {
  it("parses `@@ -1,3 +1,4 @@`", () => {
    expect(parseHunkHeader("@@ -1,3 +1,4 @@")).toEqual({ start: 0, count: 3 });
  });
  it("parses single-line `@@ -1 +1 @@`", () => {
    expect(parseHunkHeader("@@ -1 +1 @@")).toEqual({ start: 0, count: 1 });
  });
  it("parses pure-insert `@@ -3,0 +4,2 @@`", () => {
    expect(parseHunkHeader("@@ -3,0 +4,2 @@")).toEqual({ start: 3, count: 0 });
  });
  it("returns 0/0 on garbage", () => {
    expect(parseHunkHeader("not a header")).toEqual({ start: 0, count: 0 });
  });
});

describe("applyAcceptedHunks", () => {
  const base = "alpha\nbeta\ngamma\ndelta\n";
  const draft = "alpha\nBETA\ngamma\nDELTA\nepsilon\n";

  // Build hunks that match what difflib would produce. Use stable
  // hunk_ids since that's all the function inspects.
  const hunks: Hunk[] = [
    {
      hunk_id: "h1",
      header: "@@ -2,1 +2,1 @@",
      lines: ["-beta", "+BETA"],
    },
    {
      hunk_id: "h2",
      header: "@@ -4,1 +4,2 @@",
      lines: ["-delta", "+DELTA", "+epsilon"],
    },
  ];

  it("applying no hunks returns base verbatim", () => {
    expect(applyAcceptedHunks(base, hunks, new Set())).toBe(base);
  });

  it("applying all hunks returns the draft", () => {
    expect(
      applyAcceptedHunks(base, hunks, new Set(["h1", "h2"])),
    ).toBe(draft);
  });

  it("applying only h1 keeps delta, replaces beta", () => {
    expect(
      applyAcceptedHunks(base, hunks, new Set(["h1"])),
    ).toBe("alpha\nBETA\ngamma\ndelta\n");
  });

  it("applying only h2 keeps beta, rewrites delta + adds epsilon", () => {
    expect(
      applyAcceptedHunks(base, hunks, new Set(["h2"])),
    ).toBe("alpha\nbeta\ngamma\nDELTA\nepsilon\n");
  });

  it("preserves trailing newline absence", () => {
    const baseNoNl = "alpha\nbeta";
    const hunksNoNl: Hunk[] = [
      {
        hunk_id: "x",
        header: "@@ -2,1 +2,1 @@",
        lines: ["-beta", "+BETA"],
      },
    ];
    expect(applyAcceptedHunks(baseNoNl, hunksNoNl, new Set(["x"]))).toBe(
      "alpha\nBETA",
    );
  });
});

describe("saveButtonLabel", () => {
  it("disables when no hunks", () => {
    expect(saveButtonLabel(0, 0)).toEqual({ label: "No changes", enabled: false });
  });
  it("disables when zero accepted", () => {
    expect(saveButtonLabel(3, 0)).toEqual({ label: "Save 0 of 3", enabled: false });
  });
  it("collapses 'all' label when total === accepted", () => {
    expect(saveButtonLabel(3, 3).label).toBe("Save all 3 hunks");
    expect(saveButtonLabel(1, 1).label).toBe("Save 1 hunk");
  });
  it("shows N of M for partial", () => {
    expect(saveButtonLabel(5, 2).label).toBe("Save 2 of 5 hunks");
  });
});
