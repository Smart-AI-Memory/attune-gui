# attune-gui — convenience targets.
#
# Most attune-gui contributors only need the editor-frontend targets here.
# Python build + tests are driven through `uv` / `pytest` directly.

EDITOR_FRONTEND := editor-frontend
EDITOR_OUTPUT := sidecar/attune_gui/static/editor

.PHONY: build-editor lint-editor typecheck-editor dev-editor test-editor clean-editor install-editor
.PHONY: regen-templates regen-all

install-editor:
	cd $(EDITOR_FRONTEND) && npm install

build-editor:
	cd $(EDITOR_FRONTEND) && npm ci && npm run build
	@echo ""
	@echo "Bundle written to $(EDITOR_OUTPUT)/"
	@ls -lh $(EDITOR_OUTPUT) 2>/dev/null || echo "  (output dir missing — build failed)"

lint-editor:
	cd $(EDITOR_FRONTEND) && npm run lint

typecheck-editor:
	cd $(EDITOR_FRONTEND) && npm run typecheck

test-editor:
	cd $(EDITOR_FRONTEND) && npm test

dev-editor:
	cd $(EDITOR_FRONTEND) && npm run dev

clean-editor:
	rm -rf $(EDITOR_OUTPUT)
	rm -rf $(EDITOR_FRONTEND)/node_modules

# Regenerate living-docs templates for the root .help/ corpus.
# Calls Anthropic for polish — costs $$ on stale features.
regen-templates:
	uv run attune-author regenerate --help-dir .help

# Single command to flush every generated artifact a PR can drift:
# living-docs templates + editor bundle. Run before pushing source
# changes to sidecar/** or editor-frontend/src/**.
regen-all: regen-templates build-editor
	@echo ""
	@echo "regen-all complete. Verify with: git status"
