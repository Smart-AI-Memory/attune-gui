import { describe, it, expect } from "vitest";
import { inferContext, AutocompleteCache } from "./autocomplete";

describe("inferContext", () => {
  it("detects `[[partial` body refs as alias completion", () => {
    const text = "body text [[par";
    const pos = text.length;
    const ctx = inferContext(text, pos);
    expect(ctx).not.toBeNull();
    expect(ctx?.kind).toBe("alias");
    expect(ctx?.prefix).toBe("par");
    expect(ctx?.from).toBe(text.length - 3);
    expect(ctx?.to).toBe(pos);
  });

  it("detects `[[` with empty prefix", () => {
    const text = "see [[";
    const ctx = inferContext(text, text.length);
    expect(ctx?.kind).toBe("alias");
    expect(ctx?.prefix).toBe("");
  });

  it("does not fire for `[partial` (single bracket)", () => {
    const text = "see [partial";
    expect(inferContext(text, text.length)).toBeNull();
  });

  it("detects `tags:` frontmatter context", () => {
    const text = "---\ntype: concept\ntags: [a, b";
    const pos = text.length;
    const ctx = inferContext(text, pos);
    expect(ctx).not.toBeNull();
    expect(ctx?.kind).toBe("tag");
    expect(ctx?.prefix).toBe("b");
  });

  it("detects `aliases:` frontmatter context", () => {
    const text = "---\ntype: concept\naliases: [foo, bar";
    const ctx = inferContext(text, text.length);
    expect(ctx?.kind).toBe("alias");
    expect(ctx?.prefix).toBe("bar");
  });

  it("ignores body lines that look like `tags:`", () => {
    // Outside the frontmatter block — should not trigger.
    const text = "---\ntype: concept\n---\n\ntags: [no-trigger";
    expect(inferContext(text, text.length)).toBeNull();
  });

  it("returns empty prefix when cursor is right after `tags: [`", () => {
    const text = "---\ntype: concept\ntags: [";
    const ctx = inferContext(text, text.length);
    expect(ctx?.kind).toBe("tag");
    expect(ctx?.prefix).toBe("");
  });

  it("handles tags without flow-array brackets", () => {
    const text = "---\ntype: concept\ntags: alpha";
    const ctx = inferContext(text, text.length);
    expect(ctx?.kind).toBe("tag");
    expect(ctx?.prefix).toBe("alpha");
  });

  it("fires on the last line of an unterminated frontmatter (C2 regression)", () => {
    // Caught by the Haiku review pass: confirm completion still fires
    // when the closing `---` has not been typed yet — users typically
    // hit autocomplete *while* writing the frontmatter.
    const text = "---\ntype: concept\ntags: [a";
    const ctx = inferContext(text, text.length);
    expect(ctx).not.toBeNull();
    expect(ctx?.kind).toBe("tag");
  });
});

describe("AutocompleteCache", () => {
  it("hits and misses by (kind, prefix)", () => {
    const cache = new AutocompleteCache();
    cache.set({ kind: "tag", prefix: "ab", results: ["abacus", "abalone"] });
    expect(cache.get("tag", "ab")?.results).toEqual(["abacus", "abalone"]);
    expect(cache.get("tag", "AB")?.results).toEqual(["abacus", "abalone"]); // case-insensitive
    expect(cache.get("alias", "ab")).toBeUndefined();
  });

  it("clear empties the cache", () => {
    const cache = new AutocompleteCache();
    cache.set({ kind: "tag", prefix: "x", results: ["xenon"] });
    cache.clear();
    expect(cache.get("tag", "x")).toBeUndefined();
  });
});
