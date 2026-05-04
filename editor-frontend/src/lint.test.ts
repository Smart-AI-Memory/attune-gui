import { describe, it, expect } from "vitest";
import { localDiagnostics } from "./lint";
import type { ServerDiagnostic } from "./api";

// `toRange` is not exported, but we can exercise the surface by
// reading what `localDiagnostics` produces (its own ranges). The
// empty-doc guard for *server* diagnostics is exercised indirectly
// through the lint pipeline; here we lock in the localDiagnostics
// behaviour for completeness.
void ({} as ServerDiagnostic);

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
