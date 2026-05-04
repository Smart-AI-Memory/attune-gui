/**
 * Grammar fixture tests.
 *
 * We exercise the parser directly (not CodeMirror) so the tests are
 * deterministic and don't depend on DOM. For each fixture we walk the
 * tree and assert the expected Attune nodes show up at the expected
 * positions.
 */

import { describe, it, expect } from "vitest";
import { parser as baseParser } from "@lezer/markdown";
import { attuneMarkdownExtension } from "./markdown-extension";

const parser = baseParser.configure(attuneMarkdownExtension);

interface FoundNode {
  name: string;
  from: number;
  to: number;
  text: string;
}

function walk(source: string, names: string[]): FoundNode[] {
  const tree = parser.parse(source);
  const wanted = new Set(names);
  const found: FoundNode[] = [];
  tree.iterate({
    enter(node) {
      if (wanted.has(node.name)) {
        found.push({
          name: node.name,
          from: node.from,
          to: node.to,
          text: source.slice(node.from, node.to),
        });
      }
    },
  });
  return found;
}

describe("AttuneFrontMatter", () => {
  it("recognizes a leading YAML block", () => {
    const src = "---\ntype: concept\nname: Foo\n---\n\nbody";
    const nodes = walk(src, ["AttuneFrontMatter"]);
    expect(nodes).toHaveLength(1);
    expect(nodes[0].text.startsWith("---\n")).toBe(true);
    expect(nodes[0].text.trimEnd().endsWith("---")).toBe(true);
  });

  it("does not match `---` mid-document", () => {
    const src = "intro\n\n---\nnot frontmatter\n---\n";
    const nodes = walk(src, ["AttuneFrontMatter"]);
    expect(nodes).toHaveLength(0);
  });

  it("ignores unterminated frontmatter (falls back to normal markdown)", () => {
    const src = "---\nstray opener\nnothing closes it";
    const nodes = walk(src, ["AttuneFrontMatter"]);
    expect(nodes).toHaveLength(0);
  });
});

describe("AttuneDepthMarker", () => {
  it("recognizes `## Depth 1` as a depth marker", () => {
    const src = "# Title\n\n## Depth 1\n\nIntro paragraph.\n";
    const nodes = walk(src, ["AttuneDepthMarker"]);
    expect(nodes).toHaveLength(1);
    expect(nodes[0].text).toBe("## Depth 1");
  });

  it("recognizes higher depths and is case-insensitive", () => {
    const src = "## DEPTH 2\n\nbody\n\n### depth 3\n";
    const nodes = walk(src, ["AttuneDepthMarker"]);
    expect(nodes.map((n) => n.text)).toEqual(["## DEPTH 2", "### depth 3"]);
  });

  it("does not match plain headings", () => {
    const src = "# Heading\n## Subheading\n";
    const nodes = walk(src, ["AttuneDepthMarker"]);
    expect(nodes).toHaveLength(0);
  });
});

describe("AttuneAliasRef", () => {
  it("recognizes `[[alias]]` in body text", () => {
    const src = "See [[other-template]] for more.\n";
    const nodes = walk(src, ["AttuneAliasRef", "AttuneAliasName"]);
    const refs = nodes.filter((n) => n.name === "AttuneAliasRef");
    const names = nodes.filter((n) => n.name === "AttuneAliasName");
    expect(refs).toHaveLength(1);
    expect(refs[0].text).toBe("[[other-template]]");
    expect(names[0].text).toBe("other-template");
  });

  it("rejects `\\[[escape]]`", () => {
    const src = "literal: \\[[not-a-ref]]\n";
    const nodes = walk(src, ["AttuneAliasRef"]);
    expect(nodes).toHaveLength(0);
  });

  it("does not span newlines", () => {
    const src = "[[start\nend]]\n";
    const nodes = walk(src, ["AttuneAliasRef"]);
    expect(nodes).toHaveLength(0);
  });

  it("rejects empty `[[]]`", () => {
    const src = "[[]] empty\n";
    const nodes = walk(src, ["AttuneAliasRef"]);
    expect(nodes).toHaveLength(0);
  });

  it("does not fire inside fenced code blocks", () => {
    const src = "```\n[[looks-like-ref]]\n```\n\n[[real-ref]]\n";
    const nodes = walk(src, ["AttuneAliasRef"]);
    expect(nodes).toHaveLength(1);
    expect(nodes[0].text).toBe("[[real-ref]]");
  });

  it("handles multiple refs on the same line", () => {
    const src = "see [[alpha]] and [[beta]] and [[gamma]]\n";
    const nodes = walk(src, ["AttuneAliasRef"]);
    expect(nodes.map((n) => n.text)).toEqual([
      "[[alpha]]",
      "[[beta]]",
      "[[gamma]]",
    ]);
  });
});

describe("composition with standard Markdown", () => {
  it("does not break ATX heading parsing for non-Depth headings", () => {
    const src = "# Title\n\n## Real heading\n\n## Depth 1\n";
    const headings = walk(src, ["ATXHeading1", "ATXHeading2"]);
    // Two non-depth headings should still be recognized.
    expect(headings.length).toBeGreaterThanOrEqual(2);
  });

  it("realistic template parses cleanly", () => {
    const src = [
      "---",
      "type: concept",
      "name: Worked Example",
      "tags: [a, b]",
      "aliases: [worked-example]",
      "---",
      "",
      "## Depth 1",
      "",
      "Brief intro. See [[other-thing]] for more.",
      "",
      "## Depth 2",
      "",
      "More detail. `[[code-not-ref]]` should not match.",
      "",
      "```",
      "[[fenced-not-ref]]",
      "```",
      "",
      "Body ref: [[real-ref]] and escape: \\[[skip-me]].",
      "",
    ].join("\n");
    const fm = walk(src, ["AttuneFrontMatter"]);
    const depths = walk(src, ["AttuneDepthMarker"]);
    const refs = walk(src, ["AttuneAliasRef"]);
    expect(fm).toHaveLength(1);
    expect(depths.map((n) => n.text)).toEqual(["## Depth 1", "## Depth 2"]);
    expect(refs.map((n) => n.text)).toEqual(["[[other-thing]]", "[[real-ref]]"]);
  });
});
