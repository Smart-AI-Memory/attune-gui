# attune-gui — convenience targets.
#
# Most attune-gui contributors only need the editor-frontend targets here.
# Python build + tests are driven through `uv` / `pytest` directly.

EDITOR_FRONTEND := editor-frontend
EDITOR_OUTPUT := sidecar/attune_gui/static/editor

.PHONY: build-editor lint-editor typecheck-editor dev-editor test-editor clean-editor install-editor
.PHONY: regen-templates regen-all sync-hooks

# Vendored Claude Code session hooks (see specs/sibling-claude-hooks/ in the
# attune umbrella workspace). Byte-identical copies of attune-ai canonical;
# the drift-guard test enforces it. Re-sync after an upstream change.
ATTUNE_AI_ROOT ?= ../attune-ai
HOOK_FILES = security_guard.py format_on_save.py compact_warning.py spec_orient.py _state.py _resume_prompt.py _transcript_size.py _sdk_gate.py spec_audit.py

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

sync-hooks:  ## Re-copy session hooks from attune-ai canonical + refresh checksums.
	@if [ ! -d "$(ATTUNE_AI_ROOT)/plugin/hooks" ]; then \
		echo "Error: $(ATTUNE_AI_ROOT)/plugin/hooks not found. Set ATTUNE_AI_ROOT=<path>"; \
		exit 1; \
	fi
	@mkdir -p .claude/hooks
	@for f in $(HOOK_FILES); do \
		cp "$(ATTUNE_AI_ROOT)/plugin/hooks/$$f" ".claude/hooks/$$f"; \
		echo "  synced: $$f"; \
	done
	@(cd .claude/hooks && shasum -a 256 $(HOOK_FILES) > .canonical-sha256)
	@echo "✓ .claude/hooks/.canonical-sha256 refreshed"
