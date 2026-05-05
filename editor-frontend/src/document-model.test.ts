import { describe, it, expect } from "vitest";
import {
  TemplateDocument,
  splitFrontMatter,
  parseFrontMatter,
  serializeFrontMatter,
} from "./document-model";

describe("splitFrontMatter", () => {
  it("splits a basic frontmatter + body", () => {
    const src = "---\ntype: concept\nname: Foo\n---\n\nbody\n";
    const r = splitFrontMatter(src);
    expect(r.hasFrontMatter).toBe(true);
    expect(r.frontmatterText).toBe("type: concept\nname: Foo");
    expect(r.body).toBe("\nbody\n");
  });

  it("returns body-only when no frontmatter", () => {
    const r = splitFrontMatter("just body\n");
    expect(r.hasFrontMatter).toBe(false);
    expect(r.frontmatterText).toBe("");
    expect(r.body).toBe("just body\n");
  });

  it("does not match unterminated frontmatter", () => {
    const r = splitFrontMatter("---\nstray\nno close");
    expect(r.hasFrontMatter).toBe(false);
  });
});

describe("parseFrontMatter", () => {
  it("reads scalars and flow arrays", () => {
    const fm = parseFrontMatter("type: concept\nname: Foo\ntags: [a, b]");
    expect(fm.values).toEqual({ type: "concept", name: "Foo", tags: ["a", "b"] });
    expect(fm.order).toEqual(["type", "name", "tags"]);
  });

  it("preserves quoted scalars", () => {
    const fm = parseFrontMatter('summary: "hello, world"');
    expect(fm.values.summary).toBe("hello, world");
  });
});

describe("serializeFrontMatter", () => {
  it("round-trips a simple template", () => {
    const fm = parseFrontMatter("type: concept\nname: Foo\ntags: [a, b]");
    expect(serializeFrontMatter(fm)).toBe("type: concept\nname: Foo\ntags: [a, b]");
  });

  it("quotes values containing commas or spaces", () => {
    const fm = parseFrontMatter("summary: hello world");
    // hello world has a space → must be quoted on serialize
    expect(serializeFrontMatter(fm)).toBe('summary: "hello world"');
  });
});

describe("TemplateDocument", () => {
  it("round-trips through getText", () => {
    const src = "---\ntype: concept\nname: Foo\n---\n\nbody here\n";
    const doc = new TemplateDocument(src);
    expect(doc.getField("type")).toBe("concept");
    expect(doc.getBody()).toBe("\nbody here\n");
    // No edits → original text returned.
    expect(doc.getText()).toBe(src);
  });

  it("applies field edits and re-serializes", () => {
    const doc = new TemplateDocument("---\ntype: concept\nname: Foo\n---\n\nbody\n");
    doc.setField("name", "Bar");
    expect(doc.getText()).toContain("name: Bar");
    expect(doc.getText()).not.toContain("name: Foo");
  });

  it("adds new fields at end of order", () => {
    const doc = new TemplateDocument("---\ntype: concept\nname: Foo\n---\n\nbody\n");
    doc.setField("tags", ["a", "b"]);
    expect(doc.getFieldOrder()).toEqual(["type", "name", "tags"]);
    expect(doc.getText()).toContain("tags: [a, b]");
  });

  it("setText reparses frontmatter and body", () => {
    const doc = new TemplateDocument("");
    doc.setText("---\ntype: task\n---\n\nnew body\n");
    expect(doc.getField("type")).toBe("task");
    expect(doc.getBody()).toBe("\nnew body\n");
  });

  it("removeField drops the key cleanly", () => {
    const doc = new TemplateDocument("---\ntype: concept\nname: Foo\ntags: [a]\n---\n\nb\n");
    doc.removeField("tags");
    expect(doc.getFieldOrder()).toEqual(["type", "name"]);
    expect(doc.getText()).not.toContain("tags:");
  });
});
