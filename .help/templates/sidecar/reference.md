---
feature: sidecar
depth: reference
generated_at: 2026-05-23T15:23:17.087987+00:00
source_hash: 82f32c163679d9108687682ce676ff1f4f1242f118d1e8295e480bcbcb749660
status: generated
---

# Sidecar reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `CommandSpec` | — | `sidecar/attune_gui/commands.py` |
| `Config` | Resolved config snapshot. Values are post-precedence. | `sidecar/attune_gui/config.py` |
| `CorpusEntry` | — | `sidecar/attune_gui/editor_corpora.py` |
| `Registry` | In-memory snapshot of ``~/.attune/corpora.json``. | `sidecar/attune_gui/editor_corpora.py` |
| `EditorSession` | In-process state for a single ``(corpus, path)`` editing tab. | `sidecar/attune_gui/editor_session.py` |
| `PortfileData` | — | `sidecar/attune_gui/editor_sidecar.py` |
| `TemplateKpi` | Templates count + stale-vs-fresh ratio for the home tiles. | `sidecar/attune_gui/home_summary.py` |
| `JobsKpi` | Job-activity snapshot. | `sidecar/attune_gui/home_summary.py` |
| `DailyJobs` | One day's job count for the sparkline. | `sidecar/attune_gui/home_summary.py` |
| `FamilyVersion` | Installed version of one attune-* package. | `sidecar/attune_gui/home_summary.py` |
| `RecentJob` | Trimmed Job for the recent-activity panel. | `sidecar/attune_gui/home_summary.py` |
| `HomeSummary` | Everything the home page needs in one shape. | `sidecar/attune_gui/home_summary.py` |
| `Job` | — | `sidecar/attune_gui/jobs.py` |
| `JobContext` | Passed into executors so they can emit log lines. | `sidecar/attune_gui/jobs.py` |
| `JobRegistry` | Process-wide registry. One instance per app (see deps.py). | `sidecar/attune_gui/jobs.py` |
| `DocEntry` | — | `sidecar/attune_gui/living_docs_store.py` |
| `ReviewItem` | — | `sidecar/attune_gui/living_docs_store.py` |
| `LivingDocsStore` | — | `sidecar/attune_gui/living_docs_store.py` |
| `AttuneGuiMCPServer` | MCP application for attune-gui. | `sidecar/attune_gui/mcp/server.py` |
| `ErrorDetail` | — | `sidecar/attune_gui/models.py` |
| `ErrorResponse` | — | `sidecar/attune_gui/models.py` |
| `HealthResponse` | — | `sidecar/attune_gui/models.py` |
| `RagQueryRequest` | — | `sidecar/attune_gui/models.py` |
| `RagHit` | — | `sidecar/attune_gui/models.py` |
| `RagQueryResponse` | — | `sidecar/attune_gui/models.py` |
| `CreateSpecRequest` | — | `sidecar/attune_gui/routes/cowork_specs.py` |
| `AddPhaseRequest` | — | `sidecar/attune_gui/routes/cowork_specs.py` |
| `CorpusModel` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `ListResponse` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `ActiveRequest` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `RegisterRequest` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `ResolveRequest` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `ResolveResponse` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `LintRequest` | — | `sidecar/attune_gui/routes/editor_lint.py` |
| `DiagnosticModel` | — | `sidecar/attune_gui/routes/editor_lint.py` |
| `AliasInfoModel` | — | `sidecar/attune_gui/routes/editor_lint.py` |
| `TemplateResponse` | — | `sidecar/attune_gui/routes/editor_template.py` |
| `DiffRequest` | — | `sidecar/attune_gui/routes/editor_template.py` |
| `HunkModel` | — | `sidecar/attune_gui/routes/editor_template.py` |
| `DiffResponse` | — | `sidecar/attune_gui/routes/editor_template.py` |
| `SaveRequest` | — | `sidecar/attune_gui/routes/editor_template.py` |
| `SaveResponse` | — | `sidecar/attune_gui/routes/editor_template.py` |
| `RenameRequest` | — | `sidecar/attune_gui/routes/editor_ws.py` |
| `StartJobRequest` | — | `sidecar/attune_gui/routes/jobs.py` |
| `ConfigUpdate` | — | `sidecar/attune_gui/routes/living_docs.py` |
| `ScanRequest` | — | `sidecar/attune_gui/routes/living_docs.py` |
| `ProfileUpdate` | — | `sidecar/attune_gui/routes/profile.py` |
| `FakeJobContext` | Stand-in for jobs.JobContext that records log lines. | `sidecar/tests/test_commands.py` |
| `TestRequireAbsolute` | — | `sidecar/tests/test_commands.py` |
| `TestRegistry` | — | `sidecar/tests/test_commands.py` |
| `TestHelpProxies` | Phase D3: ``help.*`` executor bodies moved to attune-author. | `sidecar/tests/test_commands.py` |
| `TestRagExecutors` | — | `sidecar/tests/test_commands.py` |
| `TestAuthorProxies` | Phase D2: ``author.*`` executor bodies moved to attune-author. | `sidecar/tests/test_commands.py` |
| `TestPrecedence` | — | `sidecar/tests/test_config.py` |
| `TestFileHandling` | — | `sidecar/tests/test_config.py` |
| `TestConfigCli` | — | `sidecar/tests/test_config.py` |
| `TestErrorEnvelope` | — | `sidecar/tests/test_errors_envelope.py` |
| `TestHTTPExceptionEnvelope` | — | `sidecar/tests/test_errors_envelope.py` |
| `TestUncaughtException` | — | `sidecar/tests/test_errors_envelope.py` |
| `TestValidationEnvelope` | — | `sidecar/tests/test_errors_envelope.py` |
| `TestLivingDocsRoutes` | — | `sidecar/tests/test_living_docs.py` |
| `TestPipelineCache` | — | `sidecar/tests/test_routes_rag.py` |
| `TestRagQuery` | — | `sidecar/tests/test_routes_rag.py` |
| `TestCorpusInfo` | — | `sidecar/tests/test_routes_rag.py` |
| `TestGetWorkspace` | — | `sidecar/tests/test_workspace.py` |
| `TestSetWorkspace` | — | `sidecar/tests/test_workspace.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `atomic_write()` | Write ``text`` to ``target`` atomically; return the new mtime. | `sidecar/attune_gui/_fs.py` |
| `create_app()` | Build the FastAPI app with origin-guard, CORS, and all routers wired. | `sidecar/attune_gui/app.py` |
| `get_command()` | Return the CommandSpec for ``name``, or None if it isn't registered. | `sidecar/attune_gui/commands.py` |
| `list_commands()` | Return registered commands as JSON-serializable dicts. | `sidecar/attune_gui/commands.py` |
| `is_valid_key()` | — | `sidecar/attune_gui/config.py` |
| `known_keys()` | — | `sidecar/attune_gui/config.py` |
| `env_var_for()` | — | `sidecar/attune_gui/config.py` |
| `get()` | Return the resolved value for ``key``, applying env > file > default. | `sidecar/attune_gui/config.py` |
| `get_source()` | Tell the user where the resolved value came from. Used by ``config --list``. | `sidecar/attune_gui/config.py` |
| `load()` | Resolve all keys at once. | `sidecar/attune_gui/config.py` |
| `set_value()` | Persist ``value`` to the config file. Does not validate semantics | `sidecar/attune_gui/config.py` |
| `unset_value()` | Remove ``key`` from the config file. Returns True if it was present. | `sidecar/attune_gui/config.py` |
| `load_registry()` | Read the registry file. Returns an empty Registry if absent. | `sidecar/attune_gui/editor_corpora.py` |
| `save_registry()` | Write the registry to disk. Creates ``~/.attune/`` if needed. | `sidecar/attune_gui/editor_corpora.py` |
| `list_corpora()` | — | `sidecar/attune_gui/editor_corpora.py` |
| `get_corpus()` | — | `sidecar/attune_gui/editor_corpora.py` |
| `get_active()` | — | `sidecar/attune_gui/editor_corpora.py` |
| `set_active()` | Mark ``corpus_id`` as active. Raises ``KeyError`` if unknown. | `sidecar/attune_gui/editor_corpora.py` |
| `register()` | Register a corpus. Returns the new entry; raises ``ValueError`` if | `sidecar/attune_gui/editor_corpora.py` |
| `resolve_path()` | Find the registered corpus owning ``abs_path``. | `sidecar/attune_gui/editor_corpora.py` |
| `load_corpus()` | Instantiate a :class:`attune_rag.DirectoryCorpus` for ``corpus_id``. | `sidecar/attune_gui/editor_corpora.py` |
| `hash_text()` | Return the 16-char sha256 prefix used as the session's optimistic | `sidecar/attune_gui/editor_session.py` |
| `write_portfile()` | Write ``{pid, port, token}`` to the portfile (overwriting). | `sidecar/attune_gui/editor_sidecar.py` |
| `read_portfile()` | Return the parsed portfile or ``None`` if missing/corrupt. | `sidecar/attune_gui/editor_sidecar.py` |
| `delete_portfile()` | Remove the portfile if it exists. No-op when absent. | `sidecar/attune_gui/editor_sidecar.py` |
| `is_pid_alive()` | Return True if a process with ``pid`` is currently running. | `sidecar/attune_gui/editor_sidecar.py` |
| `is_portfile_stale()` | Return True if no fresh sidecar is reachable via the portfile. | `sidecar/attune_gui/editor_sidecar.py` |
| `portfile_context()` | Write the portfile on enter, remove on exit. Always cleans up. | `sidecar/attune_gui/editor_sidecar.py` |
| `error_envelope()` | Build the canonical ``{"detail": {"message": ..., "code": ...}}`` body. | `sidecar/attune_gui/errors.py` |
| `http_exception_handler()` | Render every :class:`HTTPException` through :func:`error_envelope`. | `sidecar/attune_gui/errors.py` |
| `request_validation_exception_handler()` | Render FastAPI's request-validation 422s through :func:`error_envelope`. | `sidecar/attune_gui/errors.py` |
| `unhandled_exception_handler()` | Last-resort handler for anything that escapes the route layer. | `sidecar/attune_gui/errors.py` |
| `install_handlers()` | Register the three handlers on ``app`` at construction time. | `sidecar/attune_gui/errors.py` |
| `sparkline_points()` | Render a list of values as an SVG ``polyline`` ``points`` string. | `sidecar/attune_gui/home_summary.py` |
| `build_home_summary()` | Build the home-page summary by composing existing accessors. | `sidecar/attune_gui/home_summary.py` |
| `get_registry()` | Return the process-global JobRegistry, creating it on first call. | `sidecar/attune_gui/jobs.py` |
| `get_store()` | Return the process-global LivingDocsStore singleton, creating it on first call. | `sidecar/attune_gui/living_docs_store.py` |
| `main()` | CLI entry point: parse args, pick a port, print SIDECAR_URL, run uvicorn. | `sidecar/attune_gui/main.py` |
| `create_server()` | — | `sidecar/attune_gui/mcp/server.py` |
| `main()` | — | `sidecar/attune_gui/mcp/server.py` |
| `gui_list_specs()` | — | `sidecar/attune_gui/mcp/tools.py` |
| `gui_get_spec()` | — | `sidecar/attune_gui/mcp/tools.py` |
| `gui_get_spec_status()` | — | `sidecar/attune_gui/mcp/tools.py` |
| `gui_list_living_docs()` | — | `sidecar/attune_gui/mcp/tools.py` |
| `gui_get_living_doc()` | — | `sidecar/attune_gui/mcp/tools.py` |
| `gui_set_spec_status()` | — | `sidecar/attune_gui/mcp/tools.py` |
| `get_dispatch()` | Tool-name → async handler. Imported by :mod:`.server`. | `sidecar/attune_gui/mcp/tools.py` |
| `list_features()` | Return the feature names from ``<help_dir>/features.yaml``. | `sidecar/attune_gui/routes/choices.py` |
| `read_file()` | Return raw file contents (UTF-8) plus the `manual` frontmatter flag for `.md` files. | `sidecar/attune_gui/routes/cowork_files.py` |
| `render_file()` | Render a Markdown file (or raw text) to an HTML fragment for the preview pane. | `sidecar/attune_gui/routes/cowork_files.py` |
| `write_file()` | Atomically replace file contents from `body["content"]`. 422 if not a string. | `sidecar/attune_gui/routes/cowork_files.py` |
| `toggle_pin()` | Set or clear ``status: manual`` on a template (templates-root only). | `sidecar/attune_gui/routes/cowork_files.py` |
| `layer_health()` | Return version + importability for each attune layer. | `sidecar/attune_gui/routes/cowork_health.py` |
| `corpus_health()` | Return current workspace, template count, and summaries.json presence. | `sidecar/attune_gui/routes/cowork_health.py` |
| `root_redirect()` | Redirect ``/`` to the default Health page. | `sidecar/attune_gui/routes/cowork_pages.py` |
| `page_home()` | Render the Home page — KPI tiles, sparkline, recent jobs, snapshot. | `sidecar/attune_gui/routes/cowork_pages.py` |
| `page_health()` | Render the Health page — per-layer version probe + corpus snapshot. | `sidecar/attune_gui/routes/cowork_pages.py` |
| `page_templates()` | Render the Templates page. ``filter`` is one of all|manual|generated|stale. | `sidecar/attune_gui/routes/cowork_pages.py` |
| `page_specs()` | Render the Specs page — feature specs grouped by project. | `sidecar/attune_gui/routes/cowork_pages.py` |
| `page_summaries()` | Render the Summaries page — inline-editable view of summaries.json. | `sidecar/attune_gui/routes/cowork_pages.py` |
| `page_preview()` | Render the Preview/Edit page for any file under a known root (templates|specs|summaries). | `sidecar/attune_gui/routes/cowork_pages.py` |
| `page_living_docs()` | Render the Living Docs page — health, composed doc rows, workspace config. | `sidecar/attune_gui/routes/cowork_pages.py` |
| `page_commands()` | Render the Commands page — clickable cards for each registered command. | `sidecar/attune_gui/routes/cowork_pages.py` |
| `page_jobs()` | Render the Jobs page — history with status, last-output, and Cancel buttons. | `sidecar/attune_gui/routes/cowork_pages.py` |
| `list_specs()` | Return a list of feature specs aggregated across all configured spec roots. | `sidecar/attune_gui/routes/cowork_specs.py` |
| `get_template()` | Return the canonical spec template body, or null when none is found. | `sidecar/attune_gui/routes/cowork_specs.py` |
| `create_spec()` | Create a new feature directory with a starter ``requirements.md``. | `sidecar/attune_gui/routes/cowork_specs.py` |
| `add_phase()` | Bootstrap the next phase file (``design.md`` or ``tasks.md``). | `sidecar/attune_gui/routes/cowork_specs.py` |
| `update_status()` | Rewrite the ``**Status**:`` line in the named phase file. | `sidecar/attune_gui/routes/cowork_specs.py` |
| `list_templates()` | List `.help/templates/*.md` for the active workspace. | `sidecar/attune_gui/routes/cowork_templates.py` |
| `list_corpora()` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `set_active()` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `register()` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `resolve()` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `healthz()` | Return ``{"status": "ok"}`` if ``token`` matches this sidecar. | `sidecar/attune_gui/routes/editor_health.py` |
| `lint()` | — | `sidecar/attune_gui/routes/editor_lint.py` |
| `autocomplete()` | — | `sidecar/attune_gui/routes/editor_lint.py` |
| `editor_page()` | Render the editor HTML shell. | `sidecar/attune_gui/routes/editor_pages.py` |
| `template_schema()` | Return the JSON schema bundled with attune-rag. | `sidecar/attune_gui/routes/editor_schema.py` |
| `get_template()` | — | `sidecar/attune_gui/routes/editor_template.py` |
| `diff_template()` | — | `sidecar/attune_gui/routes/editor_template.py` |
| `save_template()` | — | `sidecar/attune_gui/routes/editor_template.py` |
| `corpus_ws()` | File-watch + presence channel for one ``(corpus, path)`` editor tab. | `sidecar/attune_gui/routes/editor_ws.py` |
| `rename_preview()` | — | `sidecar/attune_gui/routes/editor_ws.py` |
| `rename_apply()` | — | `sidecar/attune_gui/routes/editor_ws.py` |
| `browse()` | Return directory listing for *path*. | `sidecar/attune_gui/routes/fs.py` |
| `list_topics()` | List available topic slugs, optionally filtered by type. | `sidecar/attune_gui/routes/help.py` |
| `search_topics()` | Fuzzy-search topics by query string. | `sidecar/attune_gui/routes/help.py` |
| `commands()` | List runnable commands, optionally filtered by profile. | `sidecar/attune_gui/routes/jobs.py` |
| `list_all_jobs()` | Return every job the registry knows about (newest first). | `sidecar/attune_gui/routes/jobs.py` |
| `start_job()` | Start a new job for command ``req.name`` with ``req.args``. | `sidecar/attune_gui/routes/jobs.py` |
| `get_job()` | Return one job by id. 404 if unknown. | `sidecar/attune_gui/routes/jobs.py` |
| `cancel_job()` | Cancel a running job. 404 if unknown, 409 if it isn't cancellable. | `sidecar/attune_gui/routes/jobs.py` |
| `get_config()` | Return the configured workspace path and whether `.help/` exists in it. | `sidecar/attune_gui/routes/living_docs.py` |
| `set_config()` | Persist a new workspace path and queue a manual rescan. 400 if the path isn't a directory. | `sidecar/attune_gui/routes/living_docs.py` |
| `health()` | Living Docs health summary — counts, last scan, quality scores, plus workspace path. | `sidecar/attune_gui/routes/living_docs.py` |
| `list_docs()` | Return the doc registry. ``persona`` filters to one of end-user|developer|support. | `sidecar/attune_gui/routes/living_docs.py` |
| `list_rows()` | Composed rows: docs + unreviewed queue items + regen jobs joined server-side. | `sidecar/attune_gui/routes/living_docs.py` |
| `trigger_scan()` | Queue a workspace scan. Returns immediately; scan runs in the background. | `sidecar/attune_gui/routes/living_docs.py` |
| `regenerate_doc()` | Start a regeneration job for a single doc (``feature/depth``); returns the job dict. | `sidecar/attune_gui/routes/living_docs.py` |
| `list_queue()` | Return the auto-applied review queue, optionally filtered by persona / reviewed-state. | `sidecar/attune_gui/routes/living_docs.py` |
| `approve_item()` | Mark a queue item as reviewed. 404 if the item isn't in the queue. | `sidecar/attune_gui/routes/living_docs.py` |
| `revert_item()` | Git-revert an auto-applied doc. 500 if `git checkout HEAD -- <path>` fails. | `sidecar/attune_gui/routes/living_docs.py` |
| `get_quality()` | Return the most recent RAG quality scores (faithfulness + strict accuracy). | `sidecar/attune_gui/routes/living_docs.py` |
| `git_webhook()` | Git post-commit hook entry point — queues a workspace scan tagged ``git_hook``. | `sidecar/attune_gui/routes/living_docs.py` |
| `get_profile()` | Return the active UI profile (developer | author | support). | `sidecar/attune_gui/routes/profile.py` |
| `set_profile()` | Persist a new UI profile. 400 if the value isn't in the allowed set. | `sidecar/attune_gui/routes/profile.py` |
| `query()` | Run retrieval for a query and return hits + augmented prompt. | `sidecar/attune_gui/routes/rag.py` |
| `corpus_info()` | Stats about the corpus for the current workspace. | `sidecar/attune_gui/routes/rag.py` |
| `unified_search()` | Search across HelpEngine (fuzzy/keyword) and RAG corpus in parallel. | `sidecar/attune_gui/routes/search.py` |
| `health()` | Liveness probe — returns the sidecar version and Python runtime. | `sidecar/attune_gui/routes/system.py` |
| `current_workspace()` | Return the currently configured workspace path, or null if unset. | `sidecar/attune_gui/routes/system.py` |
| `session_token()` | Return the per-process client token the UI must echo on mutating requests. | `sidecar/attune_gui/routes/system.py` |
| `merge()` | Merge and rank help + RAG hits into a unified result list. | `sidecar/attune_gui/search.py` |
| `current_session_token()` | Return the in-process session token (exposed via /api/session/token). | `sidecar/attune_gui/security.py` |
| `require_client_token()` | Raise 403 if the X-Attune-Client header doesn't match the session token. | `sidecar/attune_gui/security.py` |
| `origin_guard()` | Reject requests whose Origin isn't a localhost form. | `sidecar/attune_gui/security.py` |
| `pipeline_for()` | Return a cached :class:`attune_rag.RagPipeline` for ``workspace``. | `sidecar/attune_gui/services/rag_pipeline.py` |
| `invalidate()` | Drop the cached pipeline for ``workspace`` (or the default fallback). | `sidecar/attune_gui/services/rag_pipeline.py` |
| `workspace_from_request()` | Resolve the current workspace for HTTP route handlers. | `sidecar/attune_gui/services/rag_pipeline.py` |
| `get_workspace()` | Return the configured workspace path, or ``None`` if unset / invalid. | `sidecar/attune_gui/workspace.py` |
| `set_workspace()` | Persist a new workspace path. Raises ``ValueError`` if not a directory. | `sidecar/attune_gui/workspace.py` |
| `client()` | — | `sidecar/tests/conftest.py` |
| `session_token()` | Mint a session token for routes guarded by ``X-Attune-Client``. | `sidecar/tests/conftest.py` |
| `test_features_listed_from_help_dir()` | — | `sidecar/tests/test_choices.py` |
| `test_features_listed_from_project_path()` | — | `sidecar/tests/test_choices.py` |
| `test_neither_arg_returns_400()` | — | `sidecar/tests/test_choices.py` |
| `test_both_args_return_400()` | — | `sidecar/tests/test_choices.py` |
| `test_help_dir_missing_returns_404()` | — | `sidecar/tests/test_choices.py` |
| `test_manifest_missing_returns_404()` | — | `sidecar/tests/test_choices.py` |
| `test_manifest_malformed_returns_400()` | — | `sidecar/tests/test_choices.py` |
| `test_choicesurl_present_in_author_generate_schema()` | Regression: the dashboard form relies on this extension to | `sidecar/tests/test_choices.py` |
| `ctx()` | — | `sidecar/tests/test_commands.py` |
| `isolated()` | — | `sidecar/tests/test_config.py` |
| `client()` | — | `sidecar/tests/test_contract_attune_help.py` |
| `test_list_topics_returns_array_and_count()` | — | `sidecar/tests/test_contract_attune_help.py` |
| `test_list_topics_passes_type_filter_through()` | — | `sidecar/tests/test_contract_attune_help.py` |
| `test_list_topics_500_when_engine_raises()` | Engine errors map to a generic 500 envelope (gui's global error handler | `sidecar/tests/test_contract_attune_help.py` |
| `test_search_returns_query_results_and_count()` | — | `sidecar/tests/test_contract_attune_help.py` |
| `test_search_rejects_empty_query()` | ``q`` requires min_length=1 — Pydantic surfaces 422. | `sidecar/tests/test_contract_attune_help.py` |
| `test_search_clamps_limit_to_documented_range()` | Limits below 1 or above 50 must be rejected at the boundary. | `sidecar/tests/test_contract_attune_help.py` |
| `test_search_passes_limit_to_engine()` | — | `sidecar/tests/test_contract_attune_help.py` |
| `test_search_500_when_engine_raises()` | — | `sidecar/tests/test_contract_attune_help.py` |
| `test_engine_constructor_called_with_resolved_template_dir()` | When ``template_dir`` is provided, gui resolves it via Path.resolve() | `sidecar/tests/test_contract_attune_help.py` |
| `test_engine_constructor_called_with_none_when_no_template_dir()` | — | `sidecar/tests/test_contract_attune_help.py` |
| `client()` | Re-use the standard sidecar TestClient — mirrors other route tests. | `sidecar/tests/test_contract_attune_rag.py` |
| `test_query_response_unwraps_documented_hit_shape()` | ``RagPipeline.run`` returns Citation.hits with the 4 named attrs; | `sidecar/tests/test_contract_attune_rag.py` |
| `test_query_returns_empty_hits_when_pipeline_returns_none()` | — | `sidecar/tests/test_contract_attune_rag.py` |
| `test_query_400_when_pipeline_raises_value_error()` | Gui surfaces ValueError from attune-rag as 400 with ``code: bad_query``. | `sidecar/tests/test_contract_attune_rag.py` |
| `test_query_500_when_pipeline_run_raises_unexpected()` | Generic exceptions from attune-rag map to 500 + ``code: rag_run_failed``. | `sidecar/tests/test_contract_attune_rag.py` |
| `test_query_500_when_pipeline_construction_fails()` | attune-rag init failure (e.g. missing corpus) → 500 ``rag_init_failed``. | `sidecar/tests/test_contract_attune_rag.py` |
| `test_corpus_info_aggregates_kinds_from_entry_paths()` | gui's corpus-info derives ``kinds`` from each entry's path prefix. | `sidecar/tests/test_contract_attune_rag.py` |
| `test_corpus_info_500_when_iteration_fails()` | — | `sidecar/tests/test_contract_attune_rag.py` |
| `test_read_specs_file()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_read_404_for_missing_file()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_read_blocks_path_traversal()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_unknown_root_rejected()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_render_strips_frontmatter_and_returns_html()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_write_round_trip()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_write_requires_token()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_write_rejects_non_string_content()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_pin_sets_status_manual_in_frontmatter()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_pin_clears_status_manual()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_pin_migrates_legacy_manual_true()` | Old files with the buggy ``manual: true`` flag get migrated to | `sidecar/tests/test_cowork_files.py` |
| `test_pin_only_valid_for_templates_root()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_layers_returns_all_known_packages()` | — | `sidecar/tests/test_cowork_health.py` |
| `test_layers_handles_missing_package()` | A missing optional dep should report importable=false, not 500. | `sidecar/tests/test_cowork_health.py` |
| `test_corpus_returns_null_when_no_workspace()` | — | `sidecar/tests/test_cowork_health.py` |
| `test_corpus_counts_md_files_and_finds_summaries()` | — | `sidecar/tests/test_cowork_health.py` |
| `test_corpus_no_help_dir()` | — | `sidecar/tests/test_cowork_health.py` |
| `test_root_redirects_to_dashboard()` | — | `sidecar/tests/test_cowork_pages.py` |
| `test_dashboard_renders_sidebar()` | — | `sidecar/tests/test_cowork_pages.py` |
| `test_dashboard_home_marks_active()` | ``/dashboard`` is the new Home page; nav highlight must reflect it. | `sidecar/tests/test_cowork_pages.py` |
| `test_dashboard_home_shows_kpi_grid()` | KPI tiles for templates / fresh ratio / jobs / family must render. | `sidecar/tests/test_cowork_pages.py` |
| `test_dashboard_health_route_still_works()` | Health was demoted from ``/dashboard`` to ``/dashboard/health``. | `sidecar/tests/test_cowork_pages.py` |
| `test_page_returns_200()` | — | `sidecar/tests/test_cowork_pages.py` |
| `test_specs_page_lists_seeded_features()` | — | `sidecar/tests/test_cowork_pages.py` |
| `test_specs_page_groups_by_project()` | Federated specs from two projects render as two <details> blocks. | `sidecar/tests/test_cowork_pages.py` |
| `test_templates_page_lists_seeded_with_manual_flag()` | — | `sidecar/tests/test_cowork_pages.py` |
| `test_templates_page_filter_chip()` | — | `sidecar/tests/test_cowork_pages.py` |
| `test_preview_page_renders_markdown()` | — | `sidecar/tests/test_cowork_pages.py` |
| `test_preview_page_no_path_shows_message()` | — | `sidecar/tests/test_cowork_pages.py` |
| `test_commands_page_embeds_args_schema_per_command()` | Each command card must carry a parseable JSON schema script tag. | `sidecar/tests/test_cowork_pages.py` |
| `test_commands_page_renders_browse_buttons_for_path_widgets()` | Path-typed args should get a `Browse…` button + picker wiring. | `sidecar/tests/test_cowork_pages.py` |
| `test_specs_lists_features_with_phase_and_status()` | — | `sidecar/tests/test_cowork_specs.py` |
| `test_specs_skips_dot_dirs()` | — | `sidecar/tests/test_cowork_specs.py` |
| `test_specs_returns_empty_when_no_root()` | — | `sidecar/tests/test_cowork_specs.py` |
| `test_spec_with_no_phase_files_handled()` | — | `sidecar/tests/test_cowork_specs.py` |
| `test_specs_root_env_var_wins()` | — | `sidecar/tests/test_cowork_specs.py` |
| `test_specs_root_falls_back_to_workspace()` | — | `sidecar/tests/test_cowork_specs.py` |
| `test_specs_root_falls_back_to_workspace_docs_specs()` | Workspaces that keep specs at ``docs/specs/`` (attune-rag, attune-ai layout) | `sidecar/tests/test_cowork_specs.py` |
| `test_specs_root_prefers_specs_over_docs_specs()` | If a workspace has both ``specs/`` and ``docs/specs/``, ``specs/`` wins — | `sidecar/tests/test_cowork_specs.py` |
| `test_specs_root_walks_up_from_cwd()` | If env + workspace miss, walk up from cwd until 'specs/' is found. | `sidecar/tests/test_cowork_specs.py` |
| `test_specs_root_returns_none_when_nothing_found()` | — | `sidecar/tests/test_cowork_specs.py` |
| `token()` | — | `sidecar/tests/test_cowork_specs_authoring.py` |
| `specs_root()` | — | `sidecar/tests/test_cowork_specs_authoring.py` |
| `test_get_template_returns_content()` | — | `sidecar/tests/test_cowork_specs_authoring.py` |
| `test_get_template_returns_null_when_missing()` | — | `sidecar/tests/test_cowork_specs_authoring.py` |
| `test_create_spec_writes_requirements_from_template()` | — | `sidecar/tests/test_cowork_specs_authoring.py` |
| `test_create_spec_requires_token()` | — | `sidecar/tests/test_cowork_specs_authoring.py` |
| `test_create_spec_rejects_invalid_slug()` | — | `sidecar/tests/test_cowork_specs_authoring.py` |
| `test_create_spec_409_when_exists()` | — | `sidecar/tests/test_cowork_specs_authoring.py` |
| `test_create_spec_falls_back_when_no_template()` | Without TEMPLATE.md we should still produce a usable starter file. | `sidecar/tests/test_cowork_specs_authoring.py` |
| `test_add_design_when_requirements_exists()` | — | `sidecar/tests/test_cowork_specs_authoring.py` |
| `test_add_tasks_when_design_exists()` | — | `sidecar/tests/test_cowork_specs_authoring.py` |
| `test_add_design_blocked_without_requirements()` | — | `sidecar/tests/test_cowork_specs_authoring.py` |
| `test_add_tasks_blocked_without_design()` | — | `sidecar/tests/test_cowork_specs_authoring.py` |
| `test_add_phase_409_when_exists()` | — | `sidecar/tests/test_cowork_specs_authoring.py` |
| `test_add_phase_unknown_value()` | — | `sidecar/tests/test_cowork_specs_authoring.py` |
| `test_add_phase_404_for_unknown_feature()` | — | `sidecar/tests/test_cowork_specs_authoring.py` |
| `test_update_status_rewrites_existing_line()` | — | `sidecar/tests/test_cowork_specs_authoring.py` |
| `test_update_status_404_for_missing_phase()` | — | `sidecar/tests/test_cowork_specs_authoring.py` |
| `test_update_status_rejects_invalid_value()` | — | `sidecar/tests/test_cowork_specs_authoring.py` |
| `test_update_status_inserts_when_no_status_line()` | — | `sidecar/tests/test_cowork_specs_authoring.py` |
| `test_update_status_requires_token()` | — | `sidecar/tests/test_cowork_specs_authoring.py` |
| `test_templates_lists_with_metadata()` | — | `sidecar/tests/test_cowork_templates.py` |
| `test_templates_staleness_reflects_content_drift()` | The route's `staleness` value comes from attune-author's content-drift check. | `sidecar/tests/test_cowork_templates.py` |
| `test_templates_empty_when_no_root()` | — | `sidecar/tests/test_cowork_templates.py` |
| `test_templates_root_prefers_help_templates_subdir()` | — | `sidecar/tests/test_cowork_templates.py` |
| `test_templates_root_falls_back_to_help()` | — | `sidecar/tests/test_cowork_templates.py` |
| `test_templates_root_falls_back_to_workspace_itself()` | — | `sidecar/tests/test_cowork_templates.py` |
| `test_templates_root_returns_none_when_workspace_unset()` | — | `sidecar/tests/test_cowork_templates.py` |
| `test_templates_root_returns_none_when_no_md_files()` | — | `sidecar/tests/test_cowork_templates.py` |
| `client()` | — | `sidecar/tests/test_editor_corpus.py` |
| `test_corpus_register_requires_session_token()` | POST /api/corpus/register must reject calls without the token. | `sidecar/tests/test_editor_corpus.py` |
| `test_load_registry_empty_when_missing()` | — | `sidecar/tests/test_editor_corpus.py` |
| `test_register_creates_entry_and_persists()` | — | `sidecar/tests/test_editor_corpus.py` |
| `test_register_idempotent_on_same_path()` | — | `sidecar/tests/test_editor_corpus.py` |
| `test_register_unique_id_when_names_collide()` | — | `sidecar/tests/test_editor_corpus.py` |
| `test_register_rejects_non_directory()` | — | `sidecar/tests/test_editor_corpus.py` |
| `test_set_active_updates_pointer()` | — | `sidecar/tests/test_editor_corpus.py` |
| `test_resolve_path_finds_owning_corpus()` | — | `sidecar/tests/test_editor_corpus.py` |
| `test_resolve_path_nested_picks_deepest_root()` | If a path is inside multiple registered corpora (e.g., a parent | `sidecar/tests/test_editor_corpus.py` |
| `test_resolve_path_returns_none_when_unowned()` | — | `sidecar/tests/test_editor_corpus.py` |
| `test_list_endpoint()` | — | `sidecar/tests/test_editor_corpus.py` |
| `test_register_endpoint()` | — | `sidecar/tests/test_editor_corpus.py` |
| `test_register_endpoint_rejects_bad_path()` | — | `sidecar/tests/test_editor_corpus.py` |
| `test_active_endpoint_404s_unknown_id()` | — | `sidecar/tests/test_editor_corpus.py` |
| `test_resolve_endpoint()` | — | `sidecar/tests/test_editor_corpus.py` |
| `test_resolve_endpoint_404s_unowned()` | — | `sidecar/tests/test_editor_corpus.py` |
| `test_read_bundle_assets_returns_sentinel_when_manifest_missing()` | No manifest = developer hasn't run `make build-editor`. Return sentinels | `sidecar/tests/test_editor_pages.py` |
| `test_read_bundle_assets_returns_hashed_filenames_from_manifest()` | With a valid manifest, return the hashed JS + CSS filenames. | `sidecar/tests/test_editor_pages.py` |
| `test_read_bundle_assets_prefers_explicit_style_entry()` | If the manifest has a separate style.css entry, prefer it over main.ts.css. | `sidecar/tests/test_editor_pages.py` |
| `test_read_bundle_assets_falls_back_on_corrupt_manifest()` | A corrupt manifest logs a warning and returns sentinels. | `sidecar/tests/test_editor_pages.py` |
| `test_template_schema_endpoint()` | Returns the JSON schema bundled with attune-rag. | `sidecar/tests/test_editor_schema.py` |
| `template_file()` | — | `sidecar/tests/test_editor_session.py` |
| `test_load_snapshots_base_text_and_hash()` | — | `sidecar/tests/test_editor_session.py` |
| `test_update_draft_does_not_touch_disk()` | — | `sidecar/tests/test_editor_session.py` |
| `test_matches_base_detects_external_write()` | — | `sidecar/tests/test_editor_session.py` |
| `test_file_change_event_emitted()` | Golden flow: load → edit → external file change → event arrives. | `sidecar/tests/test_editor_session.py` |
| `test_event_dedup_no_spurious_events()` | A single change emits one event, not a stream. | `sidecar/tests/test_editor_session.py` |
| `test_stop_cancels_watcher()` | — | `sidecar/tests/test_editor_session.py` |
| `test_write_and_read_portfile()` | — | `sidecar/tests/test_editor_sidecar.py` |
| `test_read_portfile_missing_returns_none()` | — | `sidecar/tests/test_editor_sidecar.py` |
| `test_read_portfile_corrupt_returns_none()` | — | `sidecar/tests/test_editor_sidecar.py` |
| `test_read_portfile_missing_keys_returns_none()` | — | `sidecar/tests/test_editor_sidecar.py` |
| `test_delete_portfile_idempotent()` | — | `sidecar/tests/test_editor_sidecar.py` |
| `test_is_pid_alive_for_current_process()` | — | `sidecar/tests/test_editor_sidecar.py` |
| `test_is_pid_alive_rejects_invalid()` | — | `sidecar/tests/test_editor_sidecar.py` |
| `test_is_portfile_stale_when_missing()` | — | `sidecar/tests/test_editor_sidecar.py` |
| `test_is_portfile_stale_when_pid_dead()` | — | `sidecar/tests/test_editor_sidecar.py` |
| `test_is_portfile_stale_false_for_live_pid()` | — | `sidecar/tests/test_editor_sidecar.py` |
| `test_portfile_context_writes_and_cleans_up()` | — | `sidecar/tests/test_editor_sidecar.py` |
| `test_portfile_context_cleans_up_on_exception()` | — | `sidecar/tests/test_editor_sidecar.py` |
| `test_healthz_returns_ok_with_valid_token()` | — | `sidecar/tests/test_editor_sidecar.py` |
| `test_healthz_returns_401_with_bad_token()` | — | `sidecar/tests/test_editor_sidecar.py` |
| `test_healthz_requires_token()` | — | `sidecar/tests/test_editor_sidecar.py` |
| `test_hash_text_is_deterministic()` | — | `sidecar/tests/test_editor_template.py` |
| `test_hash_text_differs_on_change()` | — | `sidecar/tests/test_editor_template.py` |
| `test_hash_text_is_16_hex_chars()` | — | `sidecar/tests/test_editor_template.py` |
| `test_hash_text_handles_empty()` | — | `sidecar/tests/test_editor_template.py` |
| `test_split_returns_empty_fm_when_no_block()` | — | `sidecar/tests/test_editor_template.py` |
| `test_split_extracts_frontmatter_and_body()` | — | `sidecar/tests/test_editor_template.py` |
| `test_split_returns_original_when_no_closing_fence()` | Unclosed `---` block: nothing is parsed; whole thing is body. | `sidecar/tests/test_editor_template.py` |
| `test_split_handles_immediately_closed_fence()` | ``--- | `sidecar/tests/test_editor_template.py` |
| `test_split_handles_three_dashes_no_newline()` | `---` without a following newline returns empty fm. | `sidecar/tests/test_editor_template.py` |
| `test_parse_hunk_header_typical_form()` | ``@@ -10,3 +10,4 @@`` — 0-indexed start = 9, count = 3. | `sidecar/tests/test_editor_template.py` |
| `test_parse_hunk_header_pure_insertion_count_zero()` | ``@@ -0,0 +1,3 @@`` — count zero keeps start as-is. | `sidecar/tests/test_editor_template.py` |
| `test_parse_hunk_header_no_count_means_one()` | ``@@ -5 +5 @@`` — when count omitted, defaults to 1. | `sidecar/tests/test_editor_template.py` |
| `test_parse_hunk_header_garbage_returns_zero_zero()` | — | `sidecar/tests/test_editor_template.py` |
| `test_parse_hunk_header_parametrized()` | — | `sidecar/tests/test_editor_template.py` |
| `client()` | Override conftest client to attach the X-Attune-Client token. | `sidecar/tests/test_editor_template_routes.py` |
| `test_template_save_requires_session_token()` | POST /api/corpus/<id>/template/save must reject calls without the token. | `sidecar/tests/test_editor_template_routes.py` |
| `test_lint_requires_session_token()` | POST /api/corpus/<id>/lint must reject calls without the token. | `sidecar/tests/test_editor_template_routes.py` |
| `corpus_id()` | Register a tiny 3-template corpus and return its id. | `sidecar/tests/test_editor_template_routes.py` |
| `test_get_template_returns_split_content()` | — | `sidecar/tests/test_editor_template_routes.py` |
| `test_get_template_404_when_missing()` | — | `sidecar/tests/test_editor_template_routes.py` |
| `test_get_template_rejects_path_traversal()` | — | `sidecar/tests/test_editor_template_routes.py` |
| `test_get_template_unknown_corpus()` | — | `sidecar/tests/test_editor_template_routes.py` |
| `test_diff_returns_hunks()` | — | `sidecar/tests/test_editor_template_routes.py` |
| `test_diff_409_on_drift()` | — | `sidecar/tests/test_editor_template_routes.py` |
| `test_save_full_draft_round_trip()` | — | `sidecar/tests/test_editor_template_routes.py` |
| `test_save_409_on_drift()` | — | `sidecar/tests/test_editor_template_routes.py` |
| `test_save_path_traversal_blocked()` | — | `sidecar/tests/test_editor_template_routes.py` |
| `test_save_no_op_with_empty_accepted_hunks()` | — | `sidecar/tests/test_editor_template_routes.py` |
| `test_lint_finds_broken_alias()` | — | `sidecar/tests/test_editor_template_routes.py` |
| `test_lint_404_unknown_corpus()` | — | `sidecar/tests/test_editor_template_routes.py` |
| `test_autocomplete_tags()` | — | `sidecar/tests/test_editor_template_routes.py` |
| `test_autocomplete_aliases_returns_full_info()` | — | `sidecar/tests/test_editor_template_routes.py` |
| `test_autocomplete_404_unknown_corpus()` | — | `sidecar/tests/test_editor_template_routes.py` |
| `client()` | Override conftest client to attach the X-Attune-Client token. | `sidecar/tests/test_editor_ws.py` |
| `test_rename_apply_requires_session_token()` | POST /api/corpus/<id>/refactor/rename/apply must reject without the token. | `sidecar/tests/test_editor_ws.py` |
| `corpus()` | Three-template corpus with a shared alias to drive rename tests. | `sidecar/tests/test_editor_ws.py` |
| `test_ws_pushes_file_changed_on_external_write()` | — | `sidecar/tests/test_editor_ws.py` |
| `test_ws_second_tab_gets_duplicate_session()` | — | `sidecar/tests/test_editor_ws.py` |
| `test_ws_unknown_corpus_closes()` | — | `sidecar/tests/test_editor_ws.py` |
| `test_ws_path_traversal_blocked()` | — | `sidecar/tests/test_editor_ws.py` |
| `test_rename_preview_returns_multifile_diff()` | — | `sidecar/tests/test_editor_ws.py` |
| `test_rename_preview_does_not_write_disk()` | — | `sidecar/tests/test_editor_ws.py` |
| `test_rename_apply_writes_all_files_atomically()` | — | `sidecar/tests/test_editor_ws.py` |
| `test_rename_apply_rolls_back_on_failure()` | If a mid-stream rename fails, earlier files are restored. | `sidecar/tests/test_editor_ws.py` |
| `test_rename_preview_unknown_corpus()` | — | `sidecar/tests/test_editor_ws.py` |
| `test_rename_apply_collision_returns_409()` | — | `sidecar/tests/test_editor_ws.py` |
| `test_template_path_preview_includes_moves()` | — | `sidecar/tests/test_editor_ws.py` |
| `test_template_path_apply_moves_file_and_reports_affected()` | — | `sidecar/tests/test_editor_ws.py` |
| `test_template_path_preview_missing_source_returns_400()` | — | `sidecar/tests/test_editor_ws.py` |
| `test_template_path_preview_escapes_root_returns_400()` | — | `sidecar/tests/test_editor_ws.py` |
| `test_template_path_preview_collision_returns_409()` | — | `sidecar/tests/test_editor_ws.py` |
| `test_dict_detail_4xx_preserves_extra_keys()` | Routes can attach structured context (e.g. ``owning_path``) | `sidecar/tests/test_errors.py` |
| `test_string_detail_wraps_to_message_with_null_code()` | — | `sidecar/tests/test_errors.py` |
| `test_5xx_strips_extras_to_sanitize()` | 5xx responses must not leak structured context — only the | `sidecar/tests/test_errors.py` |
| `test_5xx_with_no_useful_detail_returns_sanitized_envelope()` | — | `sidecar/tests/test_errors.py` |
| `test_normalize_detail_dict_missing_message_defaults_to_empty_string()` | — | `sidecar/tests/test_errors.py` |
| `test_dict_detail_extras_preserved_across_4xx_codes()` | — | `sidecar/tests/test_errors.py` |
| `app()` | — | `sidecar/tests/test_errors_envelope.py` |
| `client()` | — | `sidecar/tests/test_errors_envelope.py` |
| `test_2xx_responses_are_unchanged()` | — | `sidecar/tests/test_errors_envelope.py` |
| `test_browse_lists_subdirectories()` | — | `sidecar/tests/test_fs.py` |
| `test_browse_returns_resolved_absolute_path()` | — | `sidecar/tests/test_fs.py` |
| `test_browse_sets_parent()` | — | `sidecar/tests/test_fs.py` |
| `test_browse_root_has_null_parent()` | At filesystem root, parent == path so the API returns None. | `sidecar/tests/test_fs.py` |
| `test_browse_entries_are_sorted_case_insensitive()` | — | `sidecar/tests/test_fs.py` |
| `test_browse_hides_dot_entries_by_default()` | — | `sidecar/tests/test_fs.py` |
| `test_browse_shows_attune_dot_entries()` | `.help` and `.attune` are explicitly shown — the user wants to see them. | `sidecar/tests/test_fs.py` |
| `test_browse_expands_tilde()` | — | `sidecar/tests/test_fs.py` |
| `test_browse_default_path_is_home()` | — | `sidecar/tests/test_fs.py` |
| `test_browse_nonexistent_path_returns_400()` | — | `sidecar/tests/test_fs.py` |
| `test_browse_file_path_returns_400()` | — | `sidecar/tests/test_fs.py` |
| `test_browse_unreadable_dir_returns_403()` | Permission-denied during iterdir maps to HTTP 403. | `sidecar/tests/test_fs.py` |
| `test_browse_annotate_help_flags_dirs_with_features_yaml()` | Picker UX: dirs containing `features.yaml` show as valid `.help/` | `sidecar/tests/test_fs.py` |
| `test_browse_annotate_help_current_dir_marked()` | When browsing a `.help/` dir directly, the current-dir flag fires. | `sidecar/tests/test_fs.py` |
| `test_browse_no_annotation_omits_has_manifest()` | Default path (no annotate param) preserves the original wire shape. | `sidecar/tests/test_fs.py` |
| `test_browse_annotate_project_flags_dirs_with_help_manifest_inside()` | Picker UX (project mode): valid project roots are dirs with a | `sidecar/tests/test_fs.py` |
| `test_browse_annotate_project_current_dir_marked()` | — | `sidecar/tests/test_fs.py` |
| `test_sparkline_points_empty_for_no_data()` | — | `sidecar/tests/test_home_summary.py` |
| `test_sparkline_points_normalizes_to_box()` | — | `sidecar/tests/test_home_summary.py` |
| `test_to_day_returns_iso_date()` | — | `sidecar/tests/test_home_summary.py` |
| `test_to_day_returns_none_for_missing_or_garbage()` | — | `sidecar/tests/test_home_summary.py` |
| `test_duration_seconds_between_iso_timestamps()` | — | `sidecar/tests/test_home_summary.py` |
| `test_duration_returns_none_when_missing_either_endpoint()` | — | `sidecar/tests/test_home_summary.py` |
| `test_template_kpi_empty_returns_zeros()` | — | `sidecar/tests/test_home_summary.py` |
| `test_template_kpi_counts_manual_vs_generated()` | — | `sidecar/tests/test_home_summary.py` |
| `test_jobs_kpi_empty_jobs_today_zero()` | — | `sidecar/tests/test_home_summary.py` |
| `test_jobs_kpi_today_and_week_split()` | — | `sidecar/tests/test_home_summary.py` |
| `test_recent_jobs_caps_at_limit()` | — | `sidecar/tests/test_home_summary.py` |
| `test_recent_jobs_extracts_duration()` | — | `sidecar/tests/test_home_summary.py` |
| `test_family_versions_sorts_by_slug_and_marks_importable()` | — | `sidecar/tests/test_home_summary.py` |
| `test_build_home_summary_composes_all_sources()` | build_home_summary should call each accessor and assemble a HomeSummary. | `sidecar/tests/test_home_summary.py` |
| `test_build_home_summary_fails_soft_when_accessors_raise()` | Each accessor failure is contained — page must still render. | `sidecar/tests/test_home_summary.py` |
| `test_job_to_dict_serializes_all_fields()` | — | `sidecar/tests/test_jobs.py` |
| `test_job_context_log_appends_to_job_output()` | — | `sidecar/tests/test_jobs.py` |
| `test_registry_start_runs_executor_and_records_result()` | — | `sidecar/tests/test_jobs.py` |
| `test_registry_records_error_on_failure()` | — | `sidecar/tests/test_jobs.py` |
| `test_registry_cancel_running_job()` | — | `sidecar/tests/test_jobs.py` |
| `test_registry_cancel_unknown_job_returns_false()` | — | `sidecar/tests/test_jobs.py` |
| `test_registry_cancel_finished_job_returns_false()` | — | `sidecar/tests/test_jobs.py` |
| `test_registry_get_unknown_returns_none()` | — | `sidecar/tests/test_jobs.py` |
| `test_registry_list_jobs_orders_newest_first()` | — | `sidecar/tests/test_jobs.py` |
| `test_registry_trim_drops_oldest_finished_when_over_max()` | JobRegistry holds at most max_jobs; oldest finished are dropped first. | `sidecar/tests/test_jobs.py` |
| `test_get_registry_returns_same_instance()` | — | `sidecar/tests/test_jobs.py` |
| `reset_store()` | Use a fresh LivingDocsStore per test. | `sidecar/tests/test_living_docs.py` |
| `workspace()` | Set ~/.attune-gui/config.json to point at a tmp workspace. | `sidecar/tests/test_living_docs.py` |
| `test_doc_entry_to_dict_serializes_all_fields()` | — | `sidecar/tests/test_living_docs.py` |
| `test_review_item_to_dict_serializes_all_fields()` | — | `sidecar/tests/test_living_docs.py` |
| `test_scan_walks_template_files()` | — | `sidecar/tests/test_living_docs.py` |
| `test_scan_returns_already_scanning_when_in_flight()` | — | `sidecar/tests/test_living_docs.py` |
| `test_scan_handles_missing_help_dir()` | If .help/ doesn't exist, scan returns 0 docs without crashing. | `sidecar/tests/test_living_docs.py` |
| `test_scan_filters_by_persona()` | — | `sidecar/tests/test_living_docs.py` |
| `test_get_health_returns_summary_and_per_persona()` | — | `sidecar/tests/test_living_docs.py` |
| `test_add_to_queue_creates_review_item()` | — | `sidecar/tests/test_living_docs.py` |
| `test_list_queue_filters_by_reviewed()` | — | `sidecar/tests/test_living_docs.py` |
| `test_list_queue_filters_by_persona()` | — | `sidecar/tests/test_living_docs.py` |
| `test_approve_unknown_returns_false()` | — | `sidecar/tests/test_living_docs.py` |
| `test_revert_unknown_returns_error()` | — | `sidecar/tests/test_living_docs.py` |
| `test_revert_success_drops_item()` | — | `sidecar/tests/test_living_docs.py` |
| `test_revert_git_failure_returns_error()` | — | `sidecar/tests/test_living_docs.py` |
| `test_set_quality_replaces_scores()` | — | `sidecar/tests/test_living_docs.py` |
| `test_get_store_singleton()` | — | `sidecar/tests/test_living_docs.py` |
| `test_set_config_requires_token()` | — | `sidecar/tests/test_living_docs.py` |
| `test_scan_requires_token()` | — | `sidecar/tests/test_living_docs.py` |
| `seeded_server()` | Start a real uvicorn server pre-seeded with one stale doc + one pending-review item. | `sidecar/tests/test_living_docs_e2e.py` |
| `pw_browser()` | Module-scoped Playwright browser (chromium). | `sidecar/tests/test_living_docs_e2e.py` |
| `test_nojs_page_renders_table_with_badges()` | Disable JS; verify server-rendered HTML has correct badge text for each state. | `sidecar/tests/test_living_docs_e2e.py` |
| `test_regenerate_shows_spinner_and_stays_on_page()` | Click Regenerate; row should show spinner text and the URL must not change. | `sidecar/tests/test_living_docs_e2e.py` |
| `test_approve_transitions_row_without_reload()` | Click Approve on a pending-review row; row should become 'current' in place. | `sidecar/tests/test_living_docs_e2e.py` |
| `test_project_doc_state()` | — | `sidecar/tests/test_living_docs_inline.py` |
| `reset_store()` | — | `sidecar/tests/test_living_docs_inline.py` |
| `workspace()` | — | `sidecar/tests/test_living_docs_inline.py` |
| `test_rows_endpoint_returns_correct_shape()` | — | `sidecar/tests/test_living_docs_inline.py` |
| `test_rows_endpoint_computed_state_for_stale_doc()` | — | `sidecar/tests/test_living_docs_inline.py` |
| `test_rows_endpoint_pending_review_state()` | — | `sidecar/tests/test_living_docs_inline.py` |
| `test_reason_defaults_to_none()` | — | `sidecar/tests/test_living_docs_store.py` |
| `test_reason_appears_in_to_dict()` | — | `sidecar/tests/test_living_docs_store.py` |
| `test_reason_none_serialises_as_null()` | — | `sidecar/tests/test_living_docs_store.py` |
| `test_getattr_fallback_on_report_without_stale_reasons()` | getattr(report, "stale_reasons", {}) must return {} when attribute absent. | `sidecar/tests/test_living_docs_store.py` |
| `test_scan_sync_produces_reason_none_when_no_help_dir()` | _scan_sync completes without error when .help/ is absent. | `sidecar/tests/test_living_docs_store.py` |
| `test_load_state_missing_file_starts_empty()` | — | `sidecar/tests/test_living_docs_store.py` |
| `test_load_state_corrupt_json_starts_empty()` | — | `sidecar/tests/test_living_docs_store.py` |
| `test_load_state_wrong_version_starts_empty()` | — | `sidecar/tests/test_living_docs_store.py` |
| `test_load_state_unexpected_shape_starts_empty()` | — | `sidecar/tests/test_living_docs_store.py` |
| `test_save_state_round_trips_queue_and_quality()` | — | `sidecar/tests/test_living_docs_store.py` |
| `test_save_state_writes_schema_version()` | — | `sidecar/tests/test_living_docs_store.py` |
| `test_save_state_skips_malformed_queue_entry()` | — | `sidecar/tests/test_living_docs_store.py` |
| `test_add_to_queue_persists()` | add_to_queue should persist; a second store instance sees the item. | `sidecar/tests/test_living_docs_store.py` |
| `test_set_quality_persists()` | — | `sidecar/tests/test_living_docs_store.py` |
| `test_approve_persists_reviewed_flag()` | — | `sidecar/tests/test_living_docs_store.py` |
| `test_loads_simple_kv()` | — | `sidecar/tests/test_load_dotenv.py` |
| `test_overwrites_empty_env_value()` | Empty/whitespace-only existing values should be replaced. | `sidecar/tests/test_load_dotenv.py` |
| `test_does_not_overwrite_real_existing_value()` | — | `sidecar/tests/test_load_dotenv.py` |
| `test_export_prefix_supported()` | — | `sidecar/tests/test_load_dotenv.py` |
| `test_quoted_values_unquoted()` | — | `sidecar/tests/test_load_dotenv.py` |
| `test_comments_and_blank_lines_skipped()` | — | `sidecar/tests/test_load_dotenv.py` |
| `test_no_env_file_is_noop()` | — | `sidecar/tests/test_load_dotenv.py` |
| `test_malformed_lines_silently_skipped()` | Lines without ``=`` are skipped rather than crashing the loader. | `sidecar/tests/test_load_dotenv.py` |
| `test_pick_free_port_returns_int_in_user_range()` | — | `sidecar/tests/test_main.py` |
| `test_parser_defaults_to_no_command_and_auto_port()` | — | `sidecar/tests/test_main.py` |
| `test_parser_accepts_explicit_port_and_flags()` | — | `sidecar/tests/test_main.py` |
| `test_parser_rejects_invalid_log_level()` | — | `sidecar/tests/test_main.py` |
| `test_parser_config_subcommand_has_required_action()` | ``attune-gui config`` without an action must error. | `sidecar/tests/test_main.py` |
| `test_parser_config_get_requires_key()` | — | `sidecar/tests/test_main.py` |
| `test_parser_config_list_parses_cleanly()` | — | `sidecar/tests/test_main.py` |
| `test_parser_config_set_captures_key_value()` | — | `sidecar/tests/test_main.py` |
| `test_load_dotenv_reads_cwd_dotenv()` | — | `sidecar/tests/test_main.py` |
| `test_load_dotenv_skips_comments_and_blank_lines()` | — | `sidecar/tests/test_main.py` |
| `test_load_dotenv_strips_export_prefix()` | — | `sidecar/tests/test_main.py` |
| `test_load_dotenv_does_not_overwrite_real_env()` | — | `sidecar/tests/test_main.py` |
| `test_load_dotenv_treats_empty_env_var_as_unset()` | A whitespace-only env var should be overwritten by a real .env value. | `sidecar/tests/test_main.py` |
| `test_config_command_get_unknown_key_returns_2()` | — | `sidecar/tests/test_main.py` |
| `test_config_command_set_unknown_key_returns_2()` | — | `sidecar/tests/test_main.py` |
| `test_config_command_unset_unknown_key_returns_2()` | — | `sidecar/tests/test_main.py` |
| `test_config_command_unknown_action_returns_2()` | — | `sidecar/tests/test_main.py` |
| `test_app_initializes_with_full_tool_registry()` | — | `sidecar/tests/test_mcp_server.py` |
| `test_unknown_tool_returns_error_envelope()` | — | `sidecar/tests/test_mcp_server.py` |
| `test_server_name_is_attune_gui()` | — | `sidecar/tests/test_mcp_server.py` |
| `test_main_entry_point_is_callable()` | — | `sidecar/tests/test_mcp_server.py` |
| `specs_root()` | Isolated specs root containing one well-formed spec ``alpha``. | `sidecar/tests/test_mcp_tools.py` |
| `workspace_with_doc()` | Workspace with one living-docs file at .help/templates/alpha/concept.md. | `sidecar/tests/test_mcp_tools.py` |
| `app()` | — | `sidecar/tests/test_mcp_tools.py` |
| `test_list_specs_returns_configured_specs()` | — | `sidecar/tests/test_mcp_tools.py` |
| `test_list_specs_with_no_roots_returns_empty()` | — | `sidecar/tests/test_mcp_tools.py` |
| `test_get_spec_returns_phase_contents()` | — | `sidecar/tests/test_mcp_tools.py` |
| `test_get_spec_rejects_invalid_slug()` | — | `sidecar/tests/test_mcp_tools.py` |
| `test_get_spec_unknown_feature_errors()` | — | `sidecar/tests/test_mcp_tools.py` |
| `test_get_spec_status_returns_most_advanced()` | — | `sidecar/tests/test_mcp_tools.py` |
| `test_get_spec_status_explicit_phase()` | — | `sidecar/tests/test_mcp_tools.py` |
| `test_get_spec_status_rejects_invalid_phase()` | — | `sidecar/tests/test_mcp_tools.py` |
| `test_set_spec_status_persists_to_disk()` | — | `sidecar/tests/test_mcp_tools.py` |
| `test_set_spec_status_rejects_invalid_status()` | — | `sidecar/tests/test_mcp_tools.py` |
| `test_set_spec_status_rejects_invalid_phase()` | — | `sidecar/tests/test_mcp_tools.py` |
| `test_set_spec_status_rejects_invalid_feature()` | — | `sidecar/tests/test_mcp_tools.py` |
| `test_set_spec_status_unknown_feature()` | — | `sidecar/tests/test_mcp_tools.py` |
| `test_set_spec_status_missing_phase_file()` | — | `sidecar/tests/test_mcp_tools.py` |
| `test_list_living_docs_returns_docs()` | — | `sidecar/tests/test_mcp_tools.py` |
| `test_get_living_doc_reads_file_content()` | — | `sidecar/tests/test_mcp_tools.py` |
| `test_get_living_doc_rejects_malformed_id()` | — | `sidecar/tests/test_mcp_tools.py` |
| `test_get_living_doc_unknown_id_errors()` | — | `sidecar/tests/test_mcp_tools.py` |
| `clear_pipeline_cache()` | Reset the module-level pipeline cache between tests. | `sidecar/tests/test_rag_workspace.py` |
| `test_none_workspace_uses_default_key()` | No workspace → pipeline stored under the empty-Path sentinel. | `sidecar/tests/test_rag_workspace.py` |
| `test_workspace_without_templates_falls_back_to_default_corpus()` | Workspace exists but has no .help/templates/ → AttuneHelpCorpus fallback. | `sidecar/tests/test_rag_workspace.py` |
| `test_workspace_with_templates_uses_directory_corpus()` | Workspace with .help/templates/ → DirectoryCorpus scoped to that path. | `sidecar/tests/test_rag_workspace.py` |
| `test_two_workspaces_get_distinct_pipelines()` | Different workspace paths → different pipeline instances. | `sidecar/tests/test_rag_workspace.py` |
| `test_same_workspace_returns_cached_pipeline()` | Same workspace path → same pipeline object (cache hit). | `sidecar/tests/test_rag_workspace.py` |
| `test_invalidate_drops_cached_pipeline()` | invalidate() removes the entry; next call creates a fresh pipeline. | `sidecar/tests/test_rag_workspace.py` |
| `test_invalidate_unknown_workspace_is_noop()` | invalidate() on an uncached workspace raises no error. | `sidecar/tests/test_rag_workspace.py` |
| `test_invalidate_does_not_affect_other_workspaces()` | invalidate(A) leaves pipeline for workspace B intact. | `sidecar/tests/test_rag_workspace.py` |
| `test_directory_corpus_reflects_templates()` | Pipeline built from a workspace returns entries from its templates dir. | `sidecar/tests/test_rag_workspace.py` |
| `test_after_invalidate_new_templates_are_picked_up()` | After invalidate, a newly added template appears in the next pipeline. | `sidecar/tests/test_rag_workspace.py` |
| `test_absolute_project_path_resolves()` | — | `sidecar/tests/test_resolve_project_paths.py` |
| `test_tilde_project_path_expands()` | — | `sidecar/tests/test_resolve_project_paths.py` |
| `test_relative_project_path_rejected()` | — | `sidecar/tests/test_resolve_project_paths.py` |
| `test_dotted_relative_project_path_rejected()` | — | `sidecar/tests/test_resolve_project_paths.py` |
| `test_legacy_relative_project_root_rejected()` | — | `sidecar/tests/test_resolve_project_paths.py` |
| `test_legacy_relative_help_dir_rejected()` | — | `sidecar/tests/test_resolve_project_paths.py` |
| `test_no_paths_uses_workspace()` | No project_path, no project_root, no help_dir → falls back to configured workspace. | `sidecar/tests/test_resolve_project_paths.py` |
| `test_no_paths_no_workspace_raises()` | No paths and no workspace configured → clear error. | `sidecar/tests/test_resolve_project_paths.py` |
| `test_explicit_project_root_skips_workspace()` | Explicit project_root / help_dir legacy args win over workspace. | `sidecar/tests/test_resolve_project_paths.py` |
| `test_help_dir_autopromotes_when_picker_landed_on_subdir()` | If help_dir resolves to .help/templates but features.yaml is in | `sidecar/tests/test_resolve_project_paths.py` |
| `test_help_dir_unchanged_when_features_yaml_present()` | If features.yaml is already in the chosen help_dir, no promotion. | `sidecar/tests/test_resolve_project_paths.py` |
| `test_help_dir_unchanged_when_neither_dir_has_manifest()` | Walk only goes one level — if neither the chosen dir nor its | `sidecar/tests/test_resolve_project_paths.py` |
| `test_project_path_autopromotes_help_dir()` | project_path convenience key also gets the auto-promotion check | `sidecar/tests/test_resolve_project_paths.py` |
| `test_topics_returns_list_and_count()` | — | `sidecar/tests/test_routes_help.py` |
| `test_topics_passes_type_filter_to_engine()` | — | `sidecar/tests/test_routes_help.py` |
| `test_topics_resolves_template_dir()` | — | `sidecar/tests/test_routes_help.py` |
| `test_topics_engine_failure_returns_500()` | — | `sidecar/tests/test_routes_help.py` |
| `test_search_returns_results_and_count()` | — | `sidecar/tests/test_routes_help.py` |
| `test_search_respects_limit()` | — | `sidecar/tests/test_routes_help.py` |
| `test_search_rejects_empty_query()` | min_length=1 on the query — FastAPI returns 422 for an empty string. | `sidecar/tests/test_routes_help.py` |
| `test_search_rejects_out_of_range_limit()` | limit must be 1..50. | `sidecar/tests/test_routes_help.py` |
| `test_search_engine_failure_returns_500()` | — | `sidecar/tests/test_routes_help.py` |
| `reset_registry()` | Use a fresh JobRegistry per test so list/cancel/get don't leak across cases. | `sidecar/tests/test_routes_jobs.py` |
| `test_commands_returns_registered_list()` | — | `sidecar/tests/test_routes_jobs.py` |
| `test_commands_filters_by_profile()` | — | `sidecar/tests/test_routes_jobs.py` |
| `test_list_jobs_empty_initially()` | — | `sidecar/tests/test_routes_jobs.py` |
| `test_start_unknown_command_returns_404()` | — | `sidecar/tests/test_routes_jobs.py` |
| `test_start_missing_required_args_returns_400()` | rag.query has required `query` field — calling without it returns 400. | `sidecar/tests/test_routes_jobs.py` |
| `test_start_returns_job_dict()` | Inject a fake command that completes immediately, then verify the job dict. | `sidecar/tests/test_routes_jobs.py` |
| `test_start_requires_session_token()` | — | `sidecar/tests/test_routes_jobs.py` |
| `test_get_unknown_job_returns_404()` | — | `sidecar/tests/test_routes_jobs.py` |
| `test_get_existing_job_returns_dict()` | — | `sidecar/tests/test_routes_jobs.py` |
| `test_cancel_unknown_job_returns_404()` | — | `sidecar/tests/test_routes_jobs.py` |
| `test_cancel_finished_job_returns_409()` | Cancellation of an already-finished job returns 409 not_cancellable. | `sidecar/tests/test_routes_jobs.py` |
| `test_cancel_requires_session_token()` | — | `sidecar/tests/test_routes_jobs.py` |
| `client()` | Override conftest client to attach the X-Attune-Client token by default. | `sidecar/tests/test_routes_profile.py` |
| `isolated_config()` | — | `sidecar/tests/test_routes_profile.py` |
| `test_set_profile_requires_session_token()` | PUT /api/profile must reject calls without X-Attune-Client. | `sidecar/tests/test_routes_profile.py` |
| `test_get_returns_default_when_unconfigured()` | — | `sidecar/tests/test_routes_profile.py` |
| `test_get_returns_stored_profile()` | — | `sidecar/tests/test_routes_profile.py` |
| `test_get_falls_back_when_stored_profile_invalid()` | An unknown profile in config falls back to the default rather than leaking. | `sidecar/tests/test_routes_profile.py` |
| `test_get_returns_default_when_config_corrupt()` | — | `sidecar/tests/test_routes_profile.py` |
| `test_set_persists_profile()` | — | `sidecar/tests/test_routes_profile.py` |
| `test_set_accepts_all_valid_profiles()` | — | `sidecar/tests/test_routes_profile.py` |
| `test_set_rejects_invalid_profile()` | — | `sidecar/tests/test_routes_profile.py` |
| `test_set_round_trips_via_get()` | — | `sidecar/tests/test_routes_profile.py` |
| `reset_cache()` | Clear the module-global pipeline cache between tests. | `sidecar/tests/test_routes_rag.py` |
| `test_session_token_is_url_safe_and_stable()` | — | `sidecar/tests/test_security.py` |
| `test_require_client_token_accepts_matching_token()` | — | `sidecar/tests/test_security.py` |
| `test_require_client_token_rejects_missing_header()` | — | `sidecar/tests/test_security.py` |
| `test_require_client_token_rejects_wrong_token()` | — | `sidecar/tests/test_security.py` |
| `test_origin_guard_allows_missing_origin()` | No Origin header (curl, server-to-server) is allowed. | `sidecar/tests/test_security.py` |
| `test_origin_guard_allows_localhost_forms()` | — | `sidecar/tests/test_security.py` |
| `test_origin_guard_allows_ipv6_loopback()` | IPv6 loopback origins must pass the localhost guard. | `sidecar/tests/test_security.py` |
| `test_origin_guard_rejects_non_localhost()` | — | `sidecar/tests/test_security.py` |
| `test_origin_guard_rejects_malformed_origin()` | An Origin without ://host parses to a bad_origin error. | `sidecar/tests/test_security.py` |
| `test_pipeline_for_caches_per_workspace()` | — | `sidecar/tests/test_services_rag_pipeline.py` |
| `test_pipeline_for_default_when_no_workspace()` | — | `sidecar/tests/test_services_rag_pipeline.py` |
| `test_invalidate_drops_cached_entry()` | — | `sidecar/tests/test_services_rag_pipeline.py` |
| `test_invalidate_unknown_workspace_is_noop()` | Bare invalidate on an absent key must not raise. | `sidecar/tests/test_services_rag_pipeline.py` |
| `test_pipeline_for_uses_directory_corpus_when_templates_dir_exists()` | — | `sidecar/tests/test_services_rag_pipeline.py` |
| `test_pipeline_for_uses_bundled_corpus_when_no_templates_dir()` | — | `sidecar/tests/test_services_rag_pipeline.py` |
| `test_routes_rag_re_exports_pipeline_for()` | ``routes.rag`` keeps ``_get_pipeline`` as a backwards-compat alias. | `sidecar/tests/test_services_rag_pipeline.py` |
| `test_routes_search_uses_canonical_pipeline_for()` | ``routes.search`` no longer crosses into ``routes.rag`` for the cache. | `sidecar/tests/test_services_rag_pipeline.py` |
| `test_commands_invalidate_uses_canonical_module()` | The author-proxy invalidate path imports from the services module. | `sidecar/tests/test_services_rag_pipeline.py` |
| `test_health_ok()` | — | `sidecar/tests/test_system.py` |
| `test_session_token_is_stable()` | — | `sidecar/tests/test_system.py` |
| `test_bad_origin_rejected()` | — | `sidecar/tests/test_system.py` |
| `test_no_origin_allowed()` | — | `sidecar/tests/test_system.py` |
| `test_mutating_requires_client_token()` | — | `sidecar/tests/test_system.py` |
| `test_rag_topic_bundled_layout()` | — | `sidecar/tests/test_unified_search.py` |
| `test_rag_topic_author_layout_concept()` | — | `sidecar/tests/test_unified_search.py` |
| `test_rag_topic_author_layout_task()` | — | `sidecar/tests/test_unified_search.py` |
| `test_rag_topic_author_layout_reference()` | — | `sidecar/tests/test_unified_search.py` |
| `test_rag_topic_root_level_file()` | — | `sidecar/tests/test_unified_search.py` |
| `test_merge_rag_only()` | — | `sidecar/tests/test_unified_search.py` |
| `test_merge_help_only()` | — | `sidecar/tests/test_unified_search.py` |
| `test_merge_both_boosts_score()` | — | `sidecar/tests/test_unified_search.py` |
| `test_merge_boost_capped_at_one()` | — | `sidecar/tests/test_unified_search.py` |
| `test_merge_sorted_descending()` | — | `sidecar/tests/test_unified_search.py` |
| `test_merge_limit_respected()` | — | `sidecar/tests/test_unified_search.py` |
| `test_merge_distinct_topics_not_combined()` | — | `sidecar/tests/test_unified_search.py` |
| `test_merge_excerpt_from_rag()` | — | `sidecar/tests/test_unified_search.py` |
| `test_merge_empty_both()` | — | `sidecar/tests/test_unified_search.py` |
| `client()` | — | `sidecar/tests/test_unified_search.py` |
| `test_endpoint_returns_merged_results()` | — | `sidecar/tests/test_unified_search.py` |
| `test_endpoint_requires_q()` | — | `sidecar/tests/test_unified_search.py` |
| `test_endpoint_rejects_short_q()` | — | `sidecar/tests/test_unified_search.py` |
| `test_endpoint_limit_param()` | — | `sidecar/tests/test_unified_search.py` |
| `test_endpoint_invalid_workspace()` | — | `sidecar/tests/test_unified_search.py` |
| `clear_rag_cache()` | — | `sidecar/tests/test_unified_search.py` |
| `test_e2e_seeded_workspace()` | Seed two templates in a workspace; both appear in unified search results. | `sidecar/tests/test_unified_search.py` |
| `test_engine_failure_degrades_gracefully()` | _help_search catches its own errors and returns []; RAG results still come through. | `sidecar/tests/test_unified_search.py` |
| `test_merge_keeps_higher_score_when_two_rag_hits_share_topic()` | Two RAG hits resolving to the same topic key must produce one | `sidecar/tests/test_unified_search.py` |
| `test_merge_keeps_higher_score_when_lower_comes_first()` | Order-independent: low-score-first should still keep the high-score hit. | `sidecar/tests/test_unified_search.py` |
| `isolated_config()` | Point CONFIG_PATH at a tmp file and clear env overrides. | `sidecar/tests/test_workspace.py` |


## Source files

- `sidecar/**`
