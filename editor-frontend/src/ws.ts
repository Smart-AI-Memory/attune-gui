/**
 * Editor WebSocket client.
 *
 * Connects to the sidecar's `/ws/corpus/<id>?path=<rel>` channel.
 * The server pushes:
 *   - `{type: "file_changed", new_hash}` when the file mtime/hash
 *     changes on disk (saves through this editor are filtered out
 *     by the session — these are external edits).
 *   - `{type: "duplicate_session"}` if another tab already owns the
 *     `(corpus, path)` key. The duplicate stays connected so the UI
 *     can render a read-only banner.
 *
 * The client auto-reconnects with linear backoff while the editor
 * tab is open. Reconnection is silent — listeners only see real
 * server events. A `connection_lost` callback fires once per
 * disconnect so the UI can dim the status indicator if it wants.
 */

export type WsEvent =
  | { type: "file_changed"; new_hash: string }
  | { type: "duplicate_session" };

export interface WsClientOptions {
  corpusId: string;
  relPath: string;
  /** Fired when a server message arrives. */
  onEvent: (event: WsEvent) => void;
  /** Fired once each time the socket closes (before any reconnect). */
  onDisconnect?: () => void;
  /** Fired each time a (re)connection succeeds. */
  onConnect?: () => void;
  /** Override for tests. Defaults to global `WebSocket`. */
  WebSocketImpl?: typeof WebSocket;
  /** First retry delay in ms. Doubles each attempt up to a 10s cap. */
  initialBackoffMs?: number;
}

export interface WsClient {
  /** Tear down the socket; no further reconnects. */
  close(): void;
  /** Current readyState (or `closed` if no socket exists). */
  readyState(): number;
}

const MAX_BACKOFF_MS = 10_000;

export function openEditorWebSocket(opts: WsClientOptions): WsClient {
  const Ws = opts.WebSocketImpl ?? WebSocket;
  const initialBackoff = opts.initialBackoffMs ?? 500;
  let socket: WebSocket | null = null;
  let backoff = initialBackoff;
  let disposed = false;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  const url = buildUrl(opts.corpusId, opts.relPath);

  function connect(): void {
    if (disposed) return;
    socket = new Ws(url);
    socket.addEventListener("open", () => {
      backoff = initialBackoff;
      opts.onConnect?.();
    });
    socket.addEventListener("message", (ev) => {
      try {
        const parsed = JSON.parse(String(ev.data)) as WsEvent;
        opts.onEvent(parsed);
      } catch {
        // Malformed payloads are ignored — only server-emitted JSON
        // is expected on this channel.
      }
    });
    socket.addEventListener("close", () => {
      socket = null;
      opts.onDisconnect?.();
      if (disposed) return;
      reconnectTimer = setTimeout(connect, backoff);
      backoff = Math.min(backoff * 2, MAX_BACKOFF_MS);
    });
  }

  connect();

  return {
    close(): void {
      disposed = true;
      if (reconnectTimer !== null) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      if (socket !== null) {
        const s = socket;
        socket = null;
        try {
          s.close();
        } catch {
          // ignore
        }
      }
    },
    readyState(): number {
      return socket === null ? Ws.CLOSED : socket.readyState;
    },
  };
}

function buildUrl(corpusId: string, relPath: string): string {
  // Bundle is served same-origin; pick ws:// vs wss:// from `location.protocol`.
  const proto =
    typeof location !== "undefined" && location.protocol === "https:"
      ? "wss:"
      : "ws:";
  const host =
    typeof location !== "undefined" ? location.host : "localhost";
  const params = new URLSearchParams({ path: relPath });
  return `${proto}//${host}/ws/corpus/${encodeURIComponent(corpusId)}?${params.toString()}`;
}
