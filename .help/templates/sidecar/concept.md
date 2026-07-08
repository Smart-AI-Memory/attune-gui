---
type: concept
name: sidecar-concept
feature: sidecar
depth: concept
generated_at: 2026-06-23T04:14:34.348797+00:00
source_hash: 6d1a3b2a6686655be45c94fbd62b43d5887dec3496603be6ca7a12500650779e
status: generated
---

# Sidecar

`attune-gui` is a local FastAPI sidecar process that sits between the desktop UI and the attune backend services — `attune-rag`, `attune-author`, and `attune-help` — brokering commands, enforcing origin rules, and exposing a typed HTTP API to the browser.

## Role in the attune family

The sidecar runs locally on your machine. When the UI wants to trigger an operation — indexing a corpus, generating a template, running a pipeline — it sends a request to `attune-gui` rather than calling backend services directly. The sidecar validates the origin, resolves configuration, dispatches the command, and streams results back.

This indirection matters for three reasons:

- **Origin safety.** `create_app()` installs a guard that only accepts requests from `localhost`, `127.0.0.1`, or `::1`, so backend services are never reachable from arbitrary browser origins.
- **Single configuration surface.** `Config` resolves all settings once at startup using a strict `env > file > default` precedence. Every route reads from that resolved snapshot rather than re-reading environment variables at request time.
- **Cancellable, profile-scoped commands.** Every operation the UI can invoke is registered as a `CommandSpec`. You can retrieve one by name with `get_command(name)` or list all commands for a profile with `list_commands(profile)`.

## Core data structures

Understanding four dataclasses gives you a complete picture of what the sidecar tracks at runtime.

**`CommandSpec`** is the unit of work the UI can request. Each spec carries a `name`, a human-readable `title`, a `domain`, an `args_schema` that validates incoming payloads, an `executor` function, a `cancellable` flag (default `True`), and a `profiles` tuple (default `('developer',)`) that controls which UI profiles expose the command.

**`Config`** is a resolved snapshot of the three workspace settings — `workspace`, `corpora_registry`, and `specs_root` — produced by calling `load()`. Use `get(key)` to read a single value and `get_source(key)` to see whether it came from an environment variable, a config file, or the built-in default.

**`Registry`** is an in-memory snapshot of `~/.attune/corpora.json`. It holds the `active` corpus identifier and a list of `CorpusEntry` objects, each describing a corpus by `id`, `name`, `path`, `kind`, and a `warn_on_edit` flag that the UI surfaces as a caution indicator.

**`EditorSession`** tracks the in-process state for a single `(corpus, path)` editing tab. Call `EditorSession.load(abs_path)` to open a session; the session records a `base_text` and `base_hash` so `matches_base()` can tell you whether the draft has diverged from what was on disk when the tab opened. Call `update_draft(text)` to record keystrokes and `next_event()` to poll for file-change events. `start()` and `stop()` control the background polling loop.

## How the pieces fit together

```
Browser UI
    │
    ▼
attune-gui  (create_app)
    ├── origin guard  →  rejects non-localhost origins
    ├── config layer  →  Config / get() / get_source()
    ├── command registry  →  CommandSpec / get_command() / list_commands()
    ├── corpus layer  →  Registry / CorpusEntry
    └── editor layer  →  EditorSession / atomic_write()
    │
    ▼
attune-rag / attune-author / attune-help
```

Routes are wired once by `create_app()`. Filesystem writes go through `atomic_write(target, text)`, which returns the new `mtime` so callers can detect concurrent modifications without a separate stat call.

## When this matters

You interact with the sidecar concept directly when you need to:

- **Register a new command** — add a `CommandSpec` to the command registry so the UI can invoke it.
- **Add a config key** — extend `_KEYS` and update `Config` so the new setting participates in `env > file > default` resolution.
- **Open an editing tab** — use `EditorSession.load()` and poll `next_event()` to keep the UI in sync with on-disk changes.
- **Restrict access by role** — set the `profiles` tuple on a `CommandSpec` to limit a command to `developer`, `author`, or `support` profiles.
