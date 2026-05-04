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

  async loadTemplate(corpusId: string, relPath: string): Promise<TemplateResponse> {
    const url = `${this.base}/api/corpus/${encodeURIComponent(corpusId)}/template?path=${encodeURIComponent(relPath)}`;
    const res = await fetch(url, { method: "GET" });
    return this.parse<TemplateResponse>(res);
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
