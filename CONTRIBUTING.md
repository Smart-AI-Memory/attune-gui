# Contributing to attune-gui

attune-gui is a hybrid project: a Python sidecar (`sidecar/`) plus a
TypeScript/React editor frontend (`editor-frontend/`) with its own
toolchain. The pre-commit hooks below cover the **Python** surface; the
frontend has its own lint/format/test via `npm` inside `editor-frontend/`.

## Dev setup (Python sidecar)

```bash
uv sync --extra dev && uv run pre-commit install
```

That installs the dev toolchain and the git pre-commit hooks. From then
on, `black`, `ruff`, `detect-secrets`, and the standard file hygiene
hooks run automatically on every commit.

To run the full suite against the whole tree (what CI enforces):

```bash
uv run pre-commit run --all-files
```

The hooks deliberately **exclude** `editor-frontend/` (use its own
`npm run lint` / `npm run format`) and the generated Vite bundle under
`sidecar/attune_gui/static/`.

The same check runs in CI on every pull request (`.github/workflows/lint.yml`)
and fails the build on any violation.

## Tests

```bash
uv run pytest                       # Python sidecar
cd editor-frontend && npm test      # frontend (Vitest)
```
