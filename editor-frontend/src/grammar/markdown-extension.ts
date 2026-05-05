/**
 * Lezer Markdown extension for Attune templates.
 *
 * Adds three node types on top of standard Markdown:
 *
 *   - `AttuneFrontMatter` — leading `---` ... `---` YAML block
 *                            (only at doc start).
 *   - `AttuneDepthMarker` — ATX heading whose text starts with `Depth N`
 *                            (case-insensitive; N is 1..N digits).
 *   - `AttuneAliasRef`    — inline `[[alias]]` reference. Excluded inside
 *                            fenced code (the inline parser does not run
 *                            there); `\[[escape]]` is treated as plain text.
 *
 * Wire into CodeMirror via:
 *
 *   markdown({ extensions: [attuneMarkdownExtension] })
 */

import { tags as t, Tag } from "@lezer/highlight";
import type {
  BlockContext,
  BlockParser,
  InlineContext,
  InlineParser,
  Line,
  MarkdownConfig,
} from "@lezer/markdown";

/** Custom highlight tags so themes can target Attune-specific tokens. */
export const attuneTags = {
  frontmatter: Tag.define(t.meta),
  depthMarker: Tag.define(t.heading),
  aliasRef: Tag.define(t.link),
  aliasMark: Tag.define(t.processingInstruction),
};

const FRONTMATTER_DELIM = "---";
const DEPTH_HEADING_RE = /^(#{1,6})\s+Depth\s+(\d+)\b/i;

// -- FrontMatter (block) -----------------------------------------------

const FrontMatterParser: BlockParser = {
  name: "AttuneFrontMatter",
  parse(cx: BlockContext, line: Line): boolean {
    if (cx.lineStart !== 0) return false;
    if (line.text !== FRONTMATTER_DELIM) return false;

    const start = cx.lineStart;
    let end = -1;

    while (cx.nextLine()) {
      if (line.text === FRONTMATTER_DELIM) {
        end = cx.lineStart + line.text.length;
        // Consume the closing delimiter so the markdown parser does not
        // re-interpret it as a thematic break.
        cx.nextLine();
        break;
      }
    }

    if (end < 0) {
      // Unterminated frontmatter — treat as not-frontmatter so the user
      // sees normal Markdown rendering until they close the block.
      return false;
    }

    cx.addElement(cx.elt("AttuneFrontMatter", start, end));
    return true;
  },
  // Run before HorizontalRule (which would otherwise consume `---`).
  before: "HorizontalRule",
};

// -- DepthMarker (block) -----------------------------------------------

const DepthMarkerParser: BlockParser = {
  name: "AttuneDepthMarker",
  parse(cx: BlockContext, line: Line): boolean {
    if (!DEPTH_HEADING_RE.test(line.text)) return false;
    const start = cx.lineStart;
    const end = cx.lineStart + line.text.length;
    cx.addElement(cx.elt("AttuneDepthMarker", start, end));
    cx.nextLine();
    return true;
  },
  // ATXHeading would otherwise consume any `#` line — we run earlier.
  before: "ATXHeading",
};

// -- AliasRef (inline) -------------------------------------------------

const OPEN_BRACKET = 91; // '['
const NEWLINE = 10;
const CLOSE_BRACKET = 93; // ']'
const BACKSLASH = 92; // '\'

const AliasRefParser: InlineParser = {
  name: "AttuneAliasRef",
  parse(cx: InlineContext, next: number, pos: number): number {
    if (next !== OPEN_BRACKET) return -1;
    if (cx.char(pos + 1) !== OPEN_BRACKET) return -1;

    // `\[[escape]]` — bail when the previous char is a backslash.
    if (pos > 0 && cx.char(pos - 1) === BACKSLASH) return -1;

    // Walk forward looking for `]]`. Reject newlines and any nested `[`.
    const end = cx.end;
    let i = pos + 2;
    while (i < end) {
      const c = cx.char(i);
      if (c === NEWLINE) return -1;
      if (c === OPEN_BRACKET) return -1;
      if (c === CLOSE_BRACKET) {
        if (cx.char(i + 1) !== CLOSE_BRACKET) return -1;
        break;
      }
      i += 1;
    }
    if (i >= end) return -1;

    const aliasFrom = pos + 2;
    const aliasTo = i;
    if (aliasTo === aliasFrom) return -1; // empty `[[]]`

    const to = aliasTo + 2; // include trailing `]]`
    const children = [
      cx.elt("AttuneAliasMark", pos, aliasFrom),
      cx.elt("AttuneAliasName", aliasFrom, aliasTo),
      cx.elt("AttuneAliasMark", aliasTo, to),
    ];
    return cx.addElement(cx.elt("AttuneAliasRef", pos, to, children));
  },
  // Run before Link so `[[…]]` is not interpreted as a Markdown link.
  before: "Link",
};

// -- Extension --------------------------------------------------------

/**
 * MarkdownConfig that adds FrontMatter, DepthMarker, and AliasRef
 * recognition. Compose with `markdown({ extensions: [...] })` from
 * `@codemirror/lang-markdown`.
 */
export const attuneMarkdownExtension: MarkdownConfig = {
  defineNodes: [
    { name: "AttuneFrontMatter", block: true, style: attuneTags.frontmatter },
    { name: "AttuneDepthMarker", block: true, style: attuneTags.depthMarker },
    { name: "AttuneAliasRef", style: attuneTags.aliasRef },
    { name: "AttuneAliasName", style: attuneTags.aliasRef },
    { name: "AttuneAliasMark", style: attuneTags.aliasMark },
  ],
  parseBlock: [FrontMatterParser, DepthMarkerParser],
  parseInline: [AliasRefParser],
};
