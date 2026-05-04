import { describe, it, expect } from "vitest";
import {
  threeWayMerge,
  applyResolutions,
  preferredTrailingNewline,
  summarize,
  type ConflictChoice,
  type MergeRegion,
} from "./three-way-merge";

const base = "alpha\nbeta\ngamma\ndelta\nepsilon\n";

describe("threeWayMerge", () => {
  it("returns one auto region when neither side changed", () => {
    const r = threeWayMerge(base, base, base);
    expect(r.hasConflict).toBe(false);
    expect(r.regions).toHaveLength(1);
    expect(r.regions[0]).toEqual({
      kind: "auto",
      lines: ["alpha", "beta", "gamma", "delta", "epsilon"],
    });
  });

  it("auto-merges when only the editor changed", () => {
    const editor = "alpha\nbeta\nGAMMA\ndelta\nepsilon\n";
    const r = threeWayMerge(base, base, editor);
    expect(r.hasConflict).toBe(false);
    const merged = applyResolutions(r.regions, {}, true);
    expect(merged).toBe(editor);
  });

  it("auto-merges when only disk changed", () => {
    const disk = "alpha\nbeta\nGAMMA\ndelta\nepsilon\n";
    const r = threeWayMerge(disk, base, base);
    expect(r.hasConflict).toBe(false);
    expect(applyResolutions(r.regions, {}, true)).toBe(disk);
  });

  it("auto-merges non-overlapping changes from each side", () => {
    const disk = "alpha\nBETA\ngamma\ndelta\nepsilon\n";
    const editor = "alpha\nbeta\ngamma\nDELTA\nepsilon\n";
    const r = threeWayMerge(disk, base, editor);
    expect(r.hasConflict).toBe(false);
    const merged = applyResolutions(r.regions, {}, true);
    expect(merged).toBe("alpha\nBETA\ngamma\nDELTA\nepsilon\n");
  });

  it("collapses identical edits as 'false conflicts' into auto regions", () => {
    const same = "alpha\nbeta\nNEW\ndelta\nepsilon\n";
    const r = threeWayMerge(same, base, same);
    expect(r.hasConflict).toBe(false);
    expect(applyResolutions(r.regions, {}, true)).toBe(same);
  });

  it("flags overlapping disagreement as a conflict region", () => {
    const disk = "alpha\nbeta\nDISK_GAMMA\ndelta\nepsilon\n";
    const editor = "alpha\nbeta\nEDITOR_GAMMA\ndelta\nepsilon\n";
    const r = threeWayMerge(disk, base, editor);
    expect(r.hasConflict).toBe(true);
    const conflict = r.regions.find((x) => x.kind === "conflict") as Extract<
      MergeRegion,
      { kind: "conflict" }
    >;
    expect(conflict.diskLines).toEqual(["DISK_GAMMA"]);
    expect(conflict.editorLines).toEqual(["EDITOR_GAMMA"]);
    expect(conflict.baseLines).toEqual(["gamma"]);
    expect(conflict.id).toBe("c0");
  });

  it("assigns stable ids to multiple conflicts in document order", () => {
    const disk = "alpha\nDISK_BETA\ngamma\nDISK_DELTA\nepsilon\n";
    const editor = "alpha\nED_BETA\ngamma\nED_DELTA\nepsilon\n";
    const r = threeWayMerge(disk, base, editor);
    const conflictIds = r.regions
      .filter((r2) => r2.kind === "conflict")
      .map((r2) => (r2 as Extract<MergeRegion, { kind: "conflict" }>).id);
    expect(conflictIds).toEqual(["c0", "c1"]);
  });
});

describe("applyResolutions", () => {
  const disk = "alpha\nbeta\nDISK_GAMMA\ndelta\nepsilon\n";
  const editor = "alpha\nbeta\nEDITOR_GAMMA\ndelta\nepsilon\n";
  const r = threeWayMerge(disk, base, editor);

  it("uses the disk side for choice 'disk'", () => {
    const merged = applyResolutions(r.regions, { c0: "disk" }, true);
    expect(merged).toBe(disk);
  });

  it("uses the editor side for choice 'editor'", () => {
    const merged = applyResolutions(r.regions, { c0: "editor" }, true);
    expect(merged).toBe(editor);
  });

  it("concatenates disk-then-editor for 'both'", () => {
    const merged = applyResolutions(r.regions, { c0: "both" }, true);
    expect(merged).toBe(
      "alpha\nbeta\nDISK_GAMMA\nEDITOR_GAMMA\ndelta\nepsilon\n",
    );
  });

  it("defaults missing resolutions to 'editor'", () => {
    expect(applyResolutions(r.regions, {}, true)).toBe(editor);
  });

  it("respects the trailingNewline flag", () => {
    expect(applyResolutions(r.regions, { c0: "disk" }, false)).toBe(
      disk.replace(/\n$/, ""),
    );
  });
});

describe("preferredTrailingNewline", () => {
  it("uses the editor's choice when the editor is non-empty", () => {
    expect(preferredTrailingNewline("disk\n", "base\n", "editor")).toBe(false);
    expect(preferredTrailingNewline("disk", "base", "editor\n")).toBe(true);
  });

  it("falls back to disk when the editor is empty", () => {
    expect(preferredTrailingNewline("disk\n", "base", "")).toBe(true);
    expect(preferredTrailingNewline("disk", "base\n", "")).toBe(false);
  });

  it("falls back to base when both disk and editor are empty", () => {
    expect(preferredTrailingNewline("", "base\n", "")).toBe(true);
    expect(preferredTrailingNewline("", "base", "")).toBe(false);
  });
});

describe("summarize", () => {
  it("counts conflict and auto regions independently", () => {
    const disk = "alpha\nbeta\nDISK\ndelta\nepsilon\n";
    const editor = "alpha\nbeta\nED\ndelta\nepsilon\n";
    const r = threeWayMerge(disk, base, editor);
    const s = summarize(r);
    expect(s.conflicts).toBe(1);
    expect(s.autoRegions).toBeGreaterThan(0);
  });

  it("reports zero conflicts on identical inputs", () => {
    const r = threeWayMerge(base, base, base);
    expect(summarize(r).conflicts).toBe(0);
  });
});

describe("end-to-end: round-trip per-region resolution", () => {
  it("user picks editor for one conflict and disk for another", () => {
    const disk = "alpha\nDISK1\ngamma\nDISK2\nepsilon\n";
    const editor = "alpha\nED1\ngamma\nED2\nepsilon\n";
    const r = threeWayMerge(disk, base, editor);
    expect(r.hasConflict).toBe(true);
    const choices: Record<string, ConflictChoice> = {
      c0: "editor",
      c1: "disk",
    };
    const merged = applyResolutions(r.regions, choices, true);
    expect(merged).toBe("alpha\nED1\ngamma\nDISK2\nepsilon\n");
  });
});
