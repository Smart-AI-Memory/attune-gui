/**
 * Thin client for the attune-gui editor JSON routes.
 *
 * The bundle runs on the same origin as the sidecar. We echo the
 * per-session token (rendered into the Jinja shell) on mutating
 * requests via the ``X-Attune-Client`` header.
 */

export interface TemplateResponse {
  rel_path: string;
  frontmatter_text: string;
  body: string;
  text: string;
  base_hash: string;
  mtime: number;
}

export interface SaveResponse {
  rel_path: string;
  new_hash: string;
  mtime: number;
}

export interface Hunk {
  hunk_id: string;
  header: string;
  lines: string[];
}

export interface DiffResponse {
  rel_path: string;
  base_hash: string;
  new_hash: string;
  hunks: Hunk[];
}

export type DiagnosticSeverity = "error" | "warning" | "info";

export interface ServerDiagnostic {
  severity: DiagnosticSeverity;
  code: string;
  message: string;
  /** 1-indexed line. */
  line: number;
  /** 1-indexed column. */
  col: number;
  end_line: number;
  end_col: number;
}

export interface AliasInfo {
  alias: string;
  template_path: string;
  template_name: string;
}

export type AutocompleteKind = "tag" | "alias";

export type RenameKind = "alias" | "tag" | "template_path";

export interface RenameHunk {
  hunk_id: string;
  header: string;
  lines: string[];
}

export interface RenameFileEdit {
  path: string;
  old_text: string;
  new_text: string;
  hunks: RenameHunk[];
}

export interface RenamePlan {
  old: string;
  new: string;
  kind: RenameKind;
  edits: RenameFileEdit[];
}

export interface RenameApplyResponse {
  affected_files: string[];
  plan: RenamePlan;
}

export interface TemplateSchemaProperty {
  type?: string | string[];
  enum?: readonly string[];
  description?: string;
  items?: TemplateSchemaProperty;
  minLength?: number;
  uniqueItems?: boolean;
}

export interface TemplateSchema {
  title?: string;
  description?: string;
  required?: readonly string[];
  properties?: Readonly<Record<string, TemplateSchemaProperty>>;
  additionalProperties?: boolean;
}

export type CorpusKind = "source" | "generated" | "ad-hoc";

export interface CorpusEntry {
  id: string;
  name: string;
  path: string;
  kind: CorpusKind;
  warn_on_edit: boolean;
}

export interface CorpusListResponse {
  active: string | null;
  corpora: CorpusEntry[];
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class EditorApi {
  constructor(
    private readonly sessionToken: string,
    private readonly base = "",
  ) {}

  async listCorpora(): Promise<CorpusListResponse> {
    const url = `${this.base}/api/corpus`;
    const res = await fetch(url, { method: "GET" });
    return this.parse<CorpusListResponse>(res);
  }

  async setActiveCorpus(id: string): Promise<CorpusEntry> {
    const url = `${this.base}/api/corpus/active`;
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Attune-Client": this.sessionToken,
      },
      body: JSON.stringify({ id }),
    });
    return this.parse<CorpusEntry>(res);
  }

  async registerCorpus(body: {
    name: string;
    path: string;
    kind?: CorpusKind;
  }): Promise<CorpusEntry> {
    const url = `${this.base}/api/corpus/register`;
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Attune-Client": this.sessionToken,
      },
      body: JSON.stringify(body),
    });
    return this.parse<CorpusEntry>(res);
  }

  async loadSchema(): Promise<TemplateSchema> {
    const url = `${this.base}/api/editor/template-schema`;
    const res = await fetch(url, { method: "GET" });
    return this.parse<TemplateSchema>(res);
  }

  async loadTemplate(corpusId: string, relPath: string): Promise<TemplateResponse> {
    const url = `${this.base}/api/corpus/${encodeURIComponent(corpusId)}/template?path=${encodeURIComponent(relPath)}`;
    const res = await fetch(url, { method: "GET" });
    return this.parse<TemplateResponse>(res);
  }

  async diffTemplate(
    corpusId: string,
    body: { path: string; draft_text: string; base_hash: string },
  ): Promise<DiffResponse> {
    const url = `${this.base}/api/corpus/${encodeURIComponent(corpusId)}/template/diff`;
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Attune-Client": this.sessionToken,
      },
      body: JSON.stringify(body),
    });
    return this.parse<DiffResponse>(res);
  }

  async saveTemplate(
    corpusId: string,
    body: { path: string; draft_text: string; base_hash: string; accepted_hunks?: string[] },
  ): Promise<SaveResponse> {
    const url = `${this.base}/api/corpus/${encodeURIComponent(corpusId)}/template/save`;
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Attune-Client": this.sessionToken,
      },
      body: JSON.stringify(body),
    });
    return this.parse<SaveResponse>(res);
  }

  async lint(
    corpusId: string,
    body: { path: string; text: string },
    signal?: AbortSignal,
  ): Promise<ServerDiagnostic[]> {
    const url = `${this.base}/api/corpus/${encodeURIComponent(corpusId)}/lint`;
    const init: RequestInit = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Attune-Client": this.sessionToken,
      },
      body: JSON.stringify(body),
    };
    if (signal) init.signal = signal;
    const res = await fetch(url, init);
    return this.parse<ServerDiagnostic[]>(res);
  }

  async renamePreview(
    corpusId: string,
    body: { old: string; new: string; kind: RenameKind },
  ): Promise<RenamePlan> {
    const url = `${this.base}/api/corpus/${encodeURIComponent(corpusId)}/refactor/rename/preview`;
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Attune-Client": this.sessionToken,
      },
      body: JSON.stringify(body),
    });
    return this.parse<RenamePlan>(res);
  }

  async renameApply(
    corpusId: string,
    body: { old: string; new: string; kind: RenameKind },
  ): Promise<RenameApplyResponse> {
    const url = `${this.base}/api/corpus/${encodeURIComponent(corpusId)}/refactor/rename/apply`;
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Attune-Client": this.sessionToken,
      },
      body: JSON.stringify(body),
    });
    return this.parse<RenameApplyResponse>(res);
  }

  async autocomplete(
    corpusId: string,
    kind: AutocompleteKind,
    prefix: string,
    limit = 50,
    signal?: AbortSignal,
  ): Promise<string[] | AliasInfo[]> {
    const url =
      `${this.base}/api/corpus/${encodeURIComponent(corpusId)}/autocomplete` +
      `?kind=${encodeURIComponent(kind)}&prefix=${encodeURIComponent(prefix)}&limit=${limit}`;
    const init: RequestInit = { method: "GET" };
    if (signal) init.signal = signal;
    const res = await fetch(url, init);
    return this.parse<string[] | AliasInfo[]>(res);
  }

  private async parse<T>(res: Response): Promise<T> {
    if (!res.ok) {
      let detail: unknown;
      try {
        detail = await res.json();
      } catch {
        // ignore
      }
      throw new ApiError(`HTTP ${res.status}`, res.status, detail);
    }
    return (await res.json()) as T;
  }
}
