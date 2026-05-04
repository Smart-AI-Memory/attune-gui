# attune-gui editor frontend

Vite + TypeScript + CodeMirror 6 frontend for the template editor.

## Build outputs

`npm run build` writes a deterministic bundle to:

```
../sidecar/attune_gui/static/editor/
  ├── editor.js     # entry bundle
  ├── editor.css    # styles
  └── editor-*.js   # async chunks (if any)
```

These artifacts **are committed to the repo**. Consumers of `attune-gui`
do not need Node at install time — the wheel ships pre-bundled assets.

## Workflow

```bash
# from repo root
make build-editor    # runs `npm ci && npm run build`
make lint-editor     # eslint + tsc
make dev-editor      # Vite dev server (uses index.html — sidecar not required for UI iteration)
```

Inside `editor-frontend/`:

```bash
npm install
npm run build       # production bundle
npm run dev         # Vite dev server
npm run lint        # eslint
npm run typecheck   # tsc --noEmit
npm test            # vitest
```

## Bundle size budget

The combined gzipped size of `editor.js` + `editor.css` must stay under
**600 KB** (per `specs/template-editor/tasks.md` testing strategy). CI
fails the build if the threshold is exceeded.
