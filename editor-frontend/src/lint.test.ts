import { describe, it, expect } from "vitest";
import { localDiagnostics } from "./lint";

describe("localDiagnostics", () => {
  it("flags unterminated frontmatter", () => {
    const diags = localDiagnostics("---\nstray\nno closing delim");
    expect(diags).toHaveLength(1);
    expect(diags[0].severity).toBe("error");
    expect(diags[0].message).toMatch(/unterminated frontmatter/i);
  });

  it("returns empty for a well-formed template", () => {
    const text = "---\ntype: concept\nname: Foo\n---\n\nbody\n";
    expect(localDiagnostics(text)).toEqual([]);
  });

  it("returns empty for body-only docs", () => {
    expect(localDiagnostics("just body\n")).toEqual([]);
  });
});
