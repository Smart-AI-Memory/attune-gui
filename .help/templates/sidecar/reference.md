---
feature: sidecar
depth: reference
generated_at: 2026-05-05T16:26:26.465662+00:00
source_hash: 46b45f3e1ca3cb6ad2d599cfd73bcd4889415b1e3f0a3ab0c887faaaa0503b10
status: generated
---

# Sidecar reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `CommandSpec` | — | `sidecar/attune_gui/commands.py` |
| `CorpusEntry` | — | `sidecar/attune_gui/editor_corpora.py` |
| `Registry` | In-memory snapshot of ``~/.attune/corpora.json``. | `sidecar/attune_gui/editor_corpora.py` |
| `EditorSession` | In-process state for a single ``(corpus, path)`` editing tab. | `sidecar/attune_gui/editor_session.py` |
| `PortfileData` | — | `sidecar/attune_gui/editor_sidecar.py` |
| `Job` | — | `sidecar/attune_gui/jobs.py` |
| `JobContext` | Passed into executors so they can emit log lines. | `sidecar/attune_gui/jobs.py` |
| `JobRegistry` | Process-wide registry. One instance per app (see deps.py). | `sidecar/attune_gui/jobs.py` |
| `DocEntry` | — | `sidecar/attune_gui/living_docs_store.py` |
| `ReviewItem` | — | `sidecar/attune_gui/living_docs_store.py` |
| `LivingDocsStore` | — | `sidecar/attune_gui/living_docs_store.py` |
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
| `TestHelpEngineFactory` | — | `sidecar/tests/test_commands.py` |
| `TestHelpExecutors` | — | `sidecar/tests/test_commands.py` |
| `TestRagExecutors` | — | `sidecar/tests/test_commands.py` |
| `TestAuthorExecutors` | — | `sidecar/tests/test_commands.py` |
| `TestAuthorRegen` | — | `sidecar/tests/test_commands.py` |
| `TestAuthorSetup` | — | `sidecar/tests/test_commands.py` |
| `TestLivingDocsRoutes` | — | `sidecar/tests/test_living_docs.py` |
| `TestPipelineCache` | — | `sidecar/tests/test_routes_rag.py` |
| `TestRagQuery` | — | `sidecar/tests/test_routes_rag.py` |
| `TestCorpusInfo` | — | `sidecar/tests/test_routes_rag.py` |
| `TestGetWorkspace` | — | `sidecar/tests/test_workspace.py` |
| `TestSetWorkspace` | — | `sidecar/tests/test_workspace.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `require_editor_submodule()` | Import ``attune_rag.editor.<name>`` or raise an HTTP 503. | `sidecar/attune_gui/_editor_dep.py` |
| `atomic_write()` | Write ``text`` to ``target`` atomically; return the new mtime. | `sidecar/attune_gui/_fs.py` |
| `create_app()` | Build the FastAPI app with origin-guard, CORS, and all routers wired. | `sidecar/attune_gui/app.py` |
| `get_command()` | Return the CommandSpec for ``name``, or None if it isn't registered. | `sidecar/attune_gui/commands.py` |
| `list_commands()` | Return registered commands as JSON-serializable dicts. | `sidecar/attune_gui/commands.py` |
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
| `get_registry()` | Return the process-global JobRegistry, creating it on first call. | `sidecar/attune_gui/jobs.py` |
| `get_store()` | Return the process-global LivingDocsStore singleton, creating it on first call. | `sidecar/attune_gui/living_docs_store.py` |
| `main()` | CLI entry point: parse args, pick a port, print SIDECAR_URL, run uvicorn. | `sidecar/attune_gui/main.py` |
| `list_features()` | Return the feature names from ``<help_dir>/features.yaml``. | `sidecar/attune_gui/routes/choices.py` |
| `read_file()` | Return raw file contents (UTF-8) plus the `manual` frontmatter flag for `.md` files. | `sidecar/attune_gui/routes/cowork_files.py` |
| `render_file()` | Render a Markdown file (or raw text) to an HTML fragment for the preview pane. | `sidecar/attune_gui/routes/cowork_files.py` |
| `write_file()` | Atomically replace file contents from `body["content"]`. 422 if not a string. | `sidecar/attune_gui/routes/cowork_files.py` |
| `toggle_pin()` | Set or clear the ``manual: true`` frontmatter flag on a template (templates-root only). | `sidecar/attune_gui/routes/cowork_files.py` |
| `layer_health()` | Return version + importability for each attune layer. | `sidecar/attune_gui/routes/cowork_health.py` |
| `corpus_health()` | Return current workspace, template count, and summaries.json presence. | `sidecar/attune_gui/routes/cowork_health.py` |
| `root_redirect()` | Redirect ``/`` to the default Health page. | `sidecar/attune_gui/routes/cowork_pages.py` |
| `page_health()` | Render the Health page — per-layer version probe + corpus snapshot. | `sidecar/attune_gui/routes/cowork_pages.py` |
| `page_templates()` | Render the Templates page. ``filter`` is one of all|manual|generated|stale. | `sidecar/attune_gui/routes/cowork_pages.py` |
| `page_specs()` | Render the Specs page — feature specs grouped by phase + status. | `sidecar/attune_gui/routes/cowork_pages.py` |
| `page_summaries()` | Render the Summaries page — inline-editable view of summaries.json. | `sidecar/attune_gui/routes/cowork_pages.py` |
| `page_preview()` | Render the Preview/Edit page for any file under a known root (templates|specs|summaries). | `sidecar/attune_gui/routes/cowork_pages.py` |
| `page_living_docs()` | Render the Living Docs page — health, composed doc rows, workspace config. | `sidecar/attune_gui/routes/cowork_pages.py` |
| `page_commands()` | Render the Commands page — clickable cards for each registered command. | `sidecar/attune_gui/routes/cowork_pages.py` |
| `page_jobs()` | Render the Jobs page — history with status, last-output, and Cancel buttons. | `sidecar/attune_gui/routes/cowork_pages.py` |
| `list_specs()` | Return a list of feature specs found under the workspace specs root. | `sidecar/attune_gui/routes/cowork_specs.py` |
| `get_template()` | Return the canonical spec template body, or null when none is found. | `sidecar/attune_gui/routes/cowork_specs.py` |
| `create_spec()` | Create a new feature directory with a starter ``requirements.md``. | `sidecar/attune_gui/routes/cowork_specs.py` |
| `add_phase()` | Bootstrap the next phase file (``design.md`` or ``tasks.md``). | `sidecar/attune_gui/routes/cowork_specs.py` |
| `update_status()` | Rewrite the ``**Status**:`` line in the named phase file. | `sidecar/attune_gui/routes/cowork_specs.py` |
| `list_templates()` | List `.help/templates/*.md` for the active workspace, with frontmatter and mtime. | `sidecar/attune_gui/routes/cowork_templates.py` |
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
| `invalidate()` | Drop the cached pipeline for a workspace so the next call rebuilds it. | `sidecar/attune_gui/routes/rag.py` |
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
| `get_workspace()` | Return the configured workspace path, or None if unset / invalid. | `sidecar/attune_gui/workspace.py` |
| `set_workspace()` | Persist a new workspace path. Raises ValueError if not a directory. | `sidecar/attune_gui/workspace.py` |
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
| `test_read_specs_file()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_read_404_for_missing_file()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_read_blocks_path_traversal()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_unknown_root_rejected()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_render_strips_frontmatter_and_returns_html()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_write_round_trip()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_write_requires_token()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_write_rejects_non_string_content()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_pin_sets_manual_true_in_frontmatter()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_pin_clears_manual_flag()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_pin_only_valid_for_templates_root()` | — | `sidecar/tests/test_cowork_files.py` |
| `test_layers_returns_all_known_packages()` | — | `sidecar/tests/test_cowork_health.py` |
| `test_layers_handles_missing_package()` | A missing optional dep should report importable=false, not 500. | `sidecar/tests/test_cowork_health.py` |
| `test_corpus_returns_null_when_no_workspace()` | — | `sidecar/tests/test_cowork_health.py` |
| `test_corpus_counts_md_files_and_finds_summaries()` | — | `sidecar/tests/test_cowork_health.py` |
| `test_corpus_no_help_dir()` | — | `sidecar/tests/test_cowork_health.py` |
| `test_root_redirects_to_dashboard()` | — | `sidecar/tests/test_cowork_pages.py` |
| `test_dashboard_renders_sidebar()` | — | `sidecar/tests/test_cowork_pages.py` |
| `test_dashboard_health_marks_active()` | — | `sidecar/tests/test_cowork_pages.py` |
| `test_page_returns_200()` | — | `sidecar/tests/test_cowork_pages.py` |
| `test_specs_page_lists_seeded_features()` | — | `sidecar/tests/test_cowork_pages.py` |
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
| `test_templates_staleness_thresholds()` | — | `sidecar/tests/test_cowork_templates.py` |
| `test_templates_empty_when_no_root()` | — | `sidecar/tests/test_cowork_templates.py` |
| `test_templates_root_prefers_help_templates_subdir()` | — | `sidecar/tests/test_cowork_templates.py` |
| `test_templates_root_falls_back_to_help()` | — | `sidecar/tests/test_cowork_templates.py` |
| `test_templates_root_falls_back_to_workspace_itself()` | — | `sidecar/tests/test_cowork_templates.py` |
| `test_templates_root_returns_none_when_workspace_unset()` | — | `sidecar/tests/test_cowork_templates.py` |
| `test_templates_root_returns_none_when_no_md_files()` | — | `sidecar/tests/test_cowork_templates.py` |
| `client()` | — | `sidecar/tests/test_editor_corpus.py` |
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
| `test_returns_module_when_present()` | — | `sidecar/tests/test_editor_dep.py` |
| `test_returns_submodule_when_present()` | — | `sidecar/tests/test_editor_dep.py` |
| `test_raises_503_when_missing()` | Simulate the PyPI scenario where attune_rag.editor doesn't ship. | `sidecar/tests/test_editor_dep.py` |
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
| `test_loads_simple_kv()` | — | `sidecar/tests/test_load_dotenv.py` |
| `test_overwrites_empty_env_value()` | Empty/whitespace-only existing values should be replaced. | `sidecar/tests/test_load_dotenv.py` |
| `test_does_not_overwrite_real_existing_value()` | — | `sidecar/tests/test_load_dotenv.py` |
| `test_export_prefix_supported()` | — | `sidecar/tests/test_load_dotenv.py` |
| `test_quoted_values_unquoted()` | — | `sidecar/tests/test_load_dotenv.py` |
| `test_comments_and_blank_lines_skipped()` | — | `sidecar/tests/test_load_dotenv.py` |
| `test_no_env_file_is_noop()` | — | `sidecar/tests/test_load_dotenv.py` |
| `test_malformed_lines_silently_skipped()` | Lines without ``=`` are skipped rather than crashing the loader. | `sidecar/tests/test_load_dotenv.py` |
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
| `isolated_config()` | — | `sidecar/tests/test_routes_profile.py` |
| `test_get_returns_default_when_unconfigured()` | — | `sidecar/tests/test_routes_profile.py` |
| `test_get_returns_stored_profile()` | — | `sidecar/tests/test_routes_profile.py` |
| `test_get_falls_back_when_stored_profile_invalid()` | An unknown profile in config falls back to the default rather than leaking. | `sidecar/tests/test_routes_profile.py` |
| `test_get_returns_default_when_config_corrupt()` | — | `sidecar/tests/test_routes_profile.py` |
| `test_set_persists_profile()` | — | `sidecar/tests/test_routes_profile.py` |
| `test_set_accepts_all_valid_profiles()` | — | `sidecar/tests/test_routes_profile.py` |
| `test_set_rejects_invalid_profile()` | — | `sidecar/tests/test_routes_profile.py` |
| `test_set_round_trips_via_get()` | — | `sidecar/tests/test_routes_profile.py` |
| `reset_cache()` | Clear the module-global pipeline cache between tests. | `sidecar/tests/test_routes_rag.py` |
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
| `isolated_config()` | Point _CONFIG_PATH at a tmp file so tests don't touch the real home dir. | `sidecar/tests/test_workspace.py` |


## Source files

- `sidecar/**`
