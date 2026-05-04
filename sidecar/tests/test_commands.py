"""Coverage for `attune_gui.commands` — helpers, registry, and executor smoke tests.

The executors all dispatch to attune-rag / attune-author / attune-help. We patch
those at their import sites and verify dispatch + return-shape + log lines —
not the third-party libraries themselves.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from attune_gui.commands import (
    COMMANDS,
    CommandSpec,
    _exec_author_generate,
    _exec_author_init,
    _exec_author_lookup,
    _exec_author_maintain,
    _exec_author_regen,
    _exec_author_setup,
    _exec_author_status,
    _exec_help_list,
    _exec_help_lookup,
    _exec_help_search,
    _exec_rag_corpus_info,
    _exec_rag_query,
    _help_engine,
    _require_absolute,
    get_command,
    list_commands,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class FakeJobContext:
    """Stand-in for jobs.JobContext that records log lines."""

    def __init__(self, job_id: str = "test-job") -> None:
        self.job_id = job_id
        self.lines: list[str] = []

    def log(self, line: str) -> None:
        self.lines.append(line)


@pytest.fixture
def ctx() -> FakeJobContext:
    return FakeJobContext()


# ---------------------------------------------------------------------------
# _require_absolute
# ---------------------------------------------------------------------------


class TestRequireAbsolute:
    def test_absolute_path_accepted(self) -> None:
        _require_absolute("project_path", "/Users/me/project")  # no raise

    def test_tilde_path_accepted(self) -> None:
        _require_absolute("project_path", "~/project")  # no raise

    def test_relative_path_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be an absolute path"):
            _require_absolute("project_path", "Users/me/project")

    def test_dotted_path_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be an absolute path"):
            _require_absolute("project_path", "./project")

    def test_error_message_includes_field_and_value(self) -> None:
        with pytest.raises(ValueError, match="project_root.*'oops'"):
            _require_absolute("project_root", "oops")


# ---------------------------------------------------------------------------
# get_command / list_commands (registry)
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_get_command_known_returns_spec(self) -> None:
        spec = get_command("help.lookup")
        assert isinstance(spec, CommandSpec)
        assert spec.name == "help.lookup"

    def test_get_command_unknown_returns_none(self) -> None:
        assert get_command("does.not.exist") is None

    def test_list_commands_no_filter_returns_all(self) -> None:
        out = list_commands()
        assert len(out) == len(COMMANDS)
        assert {c["name"] for c in out} == set(COMMANDS.keys())

    def test_list_commands_filters_by_profile(self) -> None:
        author_cmds = list_commands(profile="author")
        all_cmds = list_commands()
        # author is a strict subset of the full registry
        author_names = {c["name"] for c in author_cmds}
        all_names = {c["name"] for c in all_cmds}
        assert author_names <= all_names
        # every author command actually has "author" in its profiles tuple
        for name in author_names:
            assert "author" in COMMANDS[name].profiles

    def test_list_commands_dict_shape(self) -> None:
        for c in list_commands():
            assert set(c.keys()) >= {
                "name",
                "title",
                "domain",
                "description",
                "args_schema",
                "cancellable",
            }

    def test_list_commands_unknown_profile_returns_empty(self) -> None:
        assert list_commands(profile="nobody-has-this-profile") == []


# ---------------------------------------------------------------------------
# _help_engine (HelpEngine factory)
# ---------------------------------------------------------------------------


class TestHelpEngineFactory:
    def test_passes_resolved_template_dir(self, tmp_path: Path) -> None:
        with patch("attune_help.HelpEngine") as mock:
            _help_engine(str(tmp_path), "job-1")
        mock.assert_called_once()
        kwargs = mock.call_args.kwargs
        assert kwargs["template_dir"] == tmp_path.resolve()
        assert kwargs["renderer"] == "plain"
        assert kwargs["user_id"] == "job-1"

    def test_none_template_dir_passes_through(self) -> None:
        with patch("attune_help.HelpEngine") as mock:
            _help_engine(None, "job-2")
        kwargs = mock.call_args.kwargs
        assert kwargs["template_dir"] is None


# ---------------------------------------------------------------------------
# Help executors (smoke tests with HelpEngine mocked)
# ---------------------------------------------------------------------------


class TestHelpExecutors:
    @pytest.mark.asyncio
    async def test_lookup_returns_content_and_logs(self, ctx: FakeJobContext) -> None:
        engine = MagicMock()
        engine.lookup.return_value = "concept body"
        engine.list_topics.return_value = ["a", "b"]
        engine.generated_dir = Path("/tmp/help")  # noqa: S108
        with patch("attune_help.HelpEngine", return_value=engine):
            result = await _exec_help_lookup({"topic": "auth"}, ctx)  # type: ignore[arg-type]
        assert result["topic"] == "auth"
        assert result["depth"] == "concept"
        assert result["content"] == "concept body"
        assert result["total_topics"] == 2
        assert any("auth" in line for line in ctx.lines)

    @pytest.mark.asyncio
    async def test_lookup_missing_topic_raises(self, ctx: FakeJobContext) -> None:
        engine = MagicMock()
        engine.lookup.return_value = None
        with patch("attune_help.HelpEngine", return_value=engine):
            with pytest.raises(ValueError, match="No help found"):
                await _exec_help_lookup({"topic": "ghost"}, ctx)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_lookup_progressive_depth_walks_steps(self, ctx: FakeJobContext) -> None:
        """depth=reference should call lookup 3 times (concept → task → reference)."""
        engine = MagicMock()
        engine.lookup.return_value = "body"
        engine.list_topics.return_value = []
        engine.generated_dir = Path("/tmp/help")  # noqa: S108
        with patch("attune_help.HelpEngine", return_value=engine):
            await _exec_help_lookup({"topic": "x", "depth": "reference"}, ctx)  # type: ignore[arg-type]
        assert engine.lookup.call_count == 3

    @pytest.mark.asyncio
    async def test_search_returns_results_and_count(self, ctx: FakeJobContext) -> None:
        engine = MagicMock()
        engine.search.return_value = [("topic-a", 0.9), ("topic-b", 0.5)]
        engine.generated_dir = Path("/tmp/help")  # noqa: S108
        with patch("attune_help.HelpEngine", return_value=engine):
            result = await _exec_help_search({"query": "auth", "limit": 5}, ctx)  # type: ignore[arg-type]
        assert result["count"] == 2
        assert len(result["results"]) == 2
        engine.search.assert_called_once_with("auth", limit=5)

    @pytest.mark.asyncio
    async def test_list_returns_topics_and_count(self, ctx: FakeJobContext) -> None:
        engine = MagicMock()
        engine.list_topics.return_value = ["t1", "t2", "t3"]
        engine.generated_dir = Path("/tmp/help")  # noqa: S108
        with patch("attune_help.HelpEngine", return_value=engine):
            result = await _exec_help_list({}, ctx)  # type: ignore[arg-type]
        assert result["topics"] == ["t1", "t2", "t3"]
        assert result["count"] == 3

    @pytest.mark.asyncio
    async def test_list_passes_type_filter(self, ctx: FakeJobContext) -> None:
        engine = MagicMock()
        engine.list_topics.return_value = []
        engine.generated_dir = Path("/tmp/help")  # noqa: S108
        with patch("attune_help.HelpEngine", return_value=engine):
            await _exec_help_list({"type_filter": "concept"}, ctx)  # type: ignore[arg-type]
        engine.list_topics.assert_called_once_with(type_filter="concept")


# ---------------------------------------------------------------------------
# RAG executors (smoke)
# ---------------------------------------------------------------------------


class TestRagExecutors:
    @pytest.mark.asyncio
    async def test_query_returns_hits_and_augmented_prompt(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        hit = SimpleNamespace(
            template_path="topic/concept.md",
            category="concept",
            score=0.85,
            excerpt="…",
        )
        result_obj = SimpleNamespace(
            citation=SimpleNamespace(hits=[hit]),
            augmented_prompt="prompt body",
        )
        pipeline = MagicMock()
        pipeline.run.return_value = result_obj
        with patch("attune_gui.routes.rag._get_pipeline", return_value=pipeline):
            out = await _exec_rag_query(
                {"query": "auth flow", "k": 1, "project_path": str(tmp_path)},
                ctx,  # type: ignore[arg-type]
            )
        assert out["query"] == "auth flow"
        assert out["k"] == 1
        assert out["total_hits"] == 1
        assert out["hits"][0]["category"] == "concept"
        assert out["augmented_prompt"] == "prompt body"

    @pytest.mark.asyncio
    async def test_corpus_info_summarizes_kinds(self, ctx: FakeJobContext, tmp_path: Path) -> None:
        entries = [
            SimpleNamespace(path="security/concept.md"),
            SimpleNamespace(path="security/task.md"),
            SimpleNamespace(path="memory/concept.md"),
        ]
        pipeline = MagicMock()
        pipeline.corpus.entries.return_value = iter(entries)
        with patch("attune_gui.routes.rag._get_pipeline", return_value=pipeline):
            out = await _exec_rag_corpus_info(
                {"project_path": str(tmp_path)}, ctx  # type: ignore[arg-type]
            )
        assert out["entry_count"] == 3
        assert out["kinds"] == ["memory", "security"]


# ---------------------------------------------------------------------------
# Author executors (smoke)
# ---------------------------------------------------------------------------


class TestAuthorExecutors:
    @pytest.mark.asyncio
    async def test_status_returns_stale_and_fresh_counts(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        feat = SimpleNamespace(name="auth")
        manifest = SimpleNamespace(features={"auth": feat})
        report = SimpleNamespace(stale_count=1, current_count=4)
        with (
            patch("attune_author.manifest.load_manifest", return_value=manifest),
            patch("attune_author.staleness.check_staleness", return_value=report),
            patch("attune_author.maintenance.format_status_report", return_value="ok"),
        ):
            out = await _exec_author_status(
                {"project_root": str(tmp_path), "help_dir": str(tmp_path / ".help")},
                ctx,  # type: ignore[arg-type]
            )
        assert out["total"] == 5
        assert out["stale"] == 1
        assert out["fresh"] == 4
        assert out["report"] == "ok"

    @pytest.mark.asyncio
    async def test_init_skips_when_already_initialized(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        help_dir = tmp_path / ".help"
        help_dir.mkdir()
        (help_dir / "features.yaml").write_text("# manifest")
        out = await _exec_author_init({"project_root": str(tmp_path)}, ctx)  # type: ignore[arg-type]
        assert out["already_initialized"] is True
        assert out["manifest_path"].endswith("features.yaml")

    @pytest.mark.asyncio
    async def test_init_handles_no_proposals(self, ctx: FakeJobContext, tmp_path: Path) -> None:
        with patch("attune_author.bootstrap.scan_project", return_value=[]):
            out = await _exec_author_init({"project_root": str(tmp_path)}, ctx)  # type: ignore[arg-type]
        assert out["discovered"] == 0
        assert "No features" in out["message"]

    @pytest.mark.asyncio
    async def test_init_writes_manifest_when_features_found(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        proposals = [
            SimpleNamespace(name="auth", description="Authentication"),
            SimpleNamespace(name="memory", description="Memory subsystem"),
        ]
        manifest = SimpleNamespace(features={p.name: p for p in proposals})
        manifest_path = tmp_path / ".help" / "features.yaml"
        with (
            patch("attune_author.bootstrap.scan_project", return_value=proposals),
            patch("attune_author.bootstrap.proposals_to_manifest", return_value=manifest),
            patch("attune_author.manifest.save_manifest", return_value=manifest_path),
        ):
            out = await _exec_author_init({"project_root": str(tmp_path)}, ctx)  # type: ignore[arg-type]
        assert out["discovered"] == 2
        assert out["manifest_path"] == str(manifest_path)
        assert {f["name"] for f in out["features"]} == {"auth", "memory"}

    @pytest.mark.asyncio
    async def test_generate_unknown_feature_raises(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        manifest = SimpleNamespace(features={"auth": SimpleNamespace(name="auth")})
        with patch("attune_author.manifest.load_manifest", return_value=manifest):
            with pytest.raises(ValueError, match="not in manifest"):
                await _exec_author_generate(
                    {
                        "feature": "ghost",
                        "project_root": str(tmp_path),
                        "help_dir": str(tmp_path / ".help"),
                    },
                    ctx,  # type: ignore[arg-type]
                )

    @pytest.mark.asyncio
    async def test_generate_returns_template_summary(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        feat = SimpleNamespace(name="auth")
        manifest = SimpleNamespace(features={"auth": feat})
        concept_path = Path("/tmp/concept.md")  # noqa: S108
        task_path = Path("/tmp/task.md")  # noqa: S108
        templates = [
            SimpleNamespace(depth="concept", path=concept_path, source_hash="h1"),
            SimpleNamespace(depth="task", path=task_path, source_hash="h2"),
        ]
        result = SimpleNamespace(
            feature="auth",
            source_hash="abc123",
            matched_files=["src/auth.py"],
            templates=templates,
        )
        with (
            patch("attune_author.manifest.load_manifest", return_value=manifest),
            patch("attune_author.generator.generate_feature_templates", return_value=result),
        ):
            out = await _exec_author_generate(
                {
                    "feature": "auth",
                    "project_root": str(tmp_path),
                    "help_dir": str(tmp_path / ".help"),
                },
                ctx,  # type: ignore[arg-type]
            )
        assert out["feature"] == "auth"
        assert out["source_hash"] == "abc123"
        assert out["matched_files"] == ["src/auth.py"]
        assert len(out["templates"]) == 2

    @pytest.mark.asyncio
    async def test_lookup_unknown_query_lists_available(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        manifest = SimpleNamespace(features={"auth": object(), "memory": object()})
        with (
            patch("attune_author.manifest.load_manifest", return_value=manifest),
            patch("attune_author.manifest.resolve_topic", return_value=None),
        ):
            with pytest.raises(ValueError, match="No feature matches.*auth.*memory"):
                await _exec_author_lookup(
                    {"query": "ghost", "help_dir": str(tmp_path / ".help")},
                    ctx,  # type: ignore[arg-type]
                )

    @pytest.mark.asyncio
    async def test_lookup_missing_template_raises(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        manifest = SimpleNamespace(features={"auth": object()})
        with (
            patch("attune_author.manifest.load_manifest", return_value=manifest),
            patch("attune_author.manifest.resolve_topic", return_value="auth"),
            patch("attune_author.manifest.is_safe_feature_name", return_value=True),
        ):
            with pytest.raises(ValueError, match="No concept template"):
                await _exec_author_lookup(
                    {"query": "auth", "help_dir": str(tmp_path / ".help")},
                    ctx,  # type: ignore[arg-type]
                )

    @pytest.mark.asyncio
    async def test_lookup_returns_template_content(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        help_dir = tmp_path / ".help"
        templates_dir = help_dir / "templates" / "auth"
        templates_dir.mkdir(parents=True)
        template_file = templates_dir / "concept.md"
        template_file.write_text("# Auth concept", encoding="utf-8")

        manifest = SimpleNamespace(features={"auth": object()})
        with (
            patch("attune_author.manifest.load_manifest", return_value=manifest),
            patch("attune_author.manifest.resolve_topic", return_value="auth"),
            patch("attune_author.manifest.is_safe_feature_name", return_value=True),
        ):
            out = await _exec_author_lookup(
                {"query": "auth", "help_dir": str(help_dir)},
                ctx,  # type: ignore[arg-type]
            )
        assert out["feature"] == "auth"
        assert out["depth"] == "concept"
        assert out["content"] == "# Auth concept"

    @pytest.mark.asyncio
    async def test_maintain_dry_run_returns_counts_only(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        manifest = SimpleNamespace(features={})
        report = SimpleNamespace(stale_count=2, current_count=3, help_entries=[], stale_features=[])
        with (
            patch("attune_author.manifest.load_manifest", return_value=manifest),
            patch("attune_author.staleness.check_staleness", return_value=report),
            patch(
                "attune_author.maintenance.MaintenanceResult",
                side_effect=lambda **_: SimpleNamespace(
                    staleness=report, regenerated=[], failed=[]
                ),
            ),
        ):
            out = await _exec_author_maintain(
                {
                    "project_root": str(tmp_path),
                    "help_dir": str(tmp_path / ".help"),
                    "dry_run": True,
                },
                ctx,  # type: ignore[arg-type]
            )
        assert out["dry_run"] is True
        assert out["stale_count"] == 2
        assert out["total_count"] == 5
        assert out["regenerated"] == []

    @pytest.mark.asyncio
    async def test_maintain_zero_stale_returns_early(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        manifest = SimpleNamespace(features={})
        report = SimpleNamespace(stale_count=0, current_count=3, help_entries=[], stale_features=[])
        with (
            patch("attune_author.manifest.load_manifest", return_value=manifest),
            patch("attune_author.staleness.check_staleness", return_value=report),
            patch(
                "attune_author.maintenance.MaintenanceResult",
                side_effect=lambda **_: SimpleNamespace(
                    staleness=report, regenerated=[], failed=[]
                ),
            ),
        ):
            out = await _exec_author_maintain(
                {"project_root": str(tmp_path), "help_dir": str(tmp_path / ".help")},
                ctx,  # type: ignore[arg-type]
            )
        assert out["stale_count"] == 0
        assert out["regenerated"] == []

    @pytest.mark.asyncio
    async def test_maintain_regen_walks_stale_entries(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        """When stale_count > 0 and not dry_run, regen each stale feature."""
        feat = SimpleNamespace(name="auth")
        manifest = SimpleNamespace(features={"auth": feat})
        stale_entry = SimpleNamespace(feature="auth", is_stale=True)
        report = SimpleNamespace(
            stale_count=1,
            current_count=2,
            help_entries=[stale_entry],
            stale_features=["auth"],
        )
        gen_result = SimpleNamespace(feature="auth", templates=[1, 2, 3])
        with (
            patch("attune_author.manifest.load_manifest", return_value=manifest),
            patch("attune_author.staleness.check_staleness", return_value=report),
            patch(
                "attune_author.maintenance.MaintenanceResult",
                side_effect=lambda **_: SimpleNamespace(
                    staleness=report, regenerated=[], failed=[]
                ),
            ),
            patch(
                "attune_author.generator.generate_feature_templates",
                return_value=gen_result,
            ),
        ):
            out = await _exec_author_maintain(
                {"project_root": str(tmp_path), "help_dir": str(tmp_path / ".help")},
                ctx,  # type: ignore[arg-type]
            )
        assert out["regenerated"] == ["auth"]
        assert out["failed"] == []

    @pytest.mark.asyncio
    async def test_maintain_skips_features_missing_from_manifest(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        manifest = SimpleNamespace(features={})  # no features
        stale_entry = SimpleNamespace(feature="ghost", is_stale=True)
        report = SimpleNamespace(
            stale_count=1,
            current_count=0,
            help_entries=[stale_entry],
            stale_features=["ghost"],
        )
        with (
            patch("attune_author.manifest.load_manifest", return_value=manifest),
            patch("attune_author.staleness.check_staleness", return_value=report),
            patch(
                "attune_author.maintenance.MaintenanceResult",
                side_effect=lambda **_: SimpleNamespace(
                    staleness=report, regenerated=[], failed=[]
                ),
            ),
        ):
            out = await _exec_author_maintain(
                {"project_root": str(tmp_path), "help_dir": str(tmp_path / ".help")},
                ctx,  # type: ignore[arg-type]
            )
        # The "ghost" feature isn't in the manifest, so it's skipped — not regenerated, not failed
        assert out["regenerated"] == []
        assert out["failed"] == []
        assert any("not in manifest" in line for line in ctx.lines)

    @pytest.mark.asyncio
    async def test_generate_all_kinds_uses_full_template_list(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        """all_kinds=True should pull _ALL_TEMPLATE_NAMES and pass them to the generator."""
        feat = SimpleNamespace(name="auth")
        manifest = SimpleNamespace(features={"auth": feat})
        result = SimpleNamespace(feature="auth", source_hash="h", matched_files=[], templates=[])
        with (
            patch("attune_author.manifest.load_manifest", return_value=manifest),
            patch(
                "attune_author.generator._ALL_TEMPLATE_NAMES",
                ["concept", "task", "reference", "comparison", "error"],
                create=True,
            ),
            patch("attune_author.generator.generate_feature_templates", return_value=result) as gen,
        ):
            await _exec_author_generate(
                {
                    "feature": "auth",
                    "all_kinds": True,
                    "project_root": str(tmp_path),
                    "help_dir": str(tmp_path / ".help"),
                },
                ctx,  # type: ignore[arg-type]
            )
        # generate_feature_templates received the full list of depths
        kwargs = gen.call_args.kwargs
        assert kwargs["depths"] == ["concept", "task", "reference", "comparison", "error"]

    @pytest.mark.asyncio
    async def test_lookup_unsafe_feature_name_raises(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        """is_safe_feature_name rejection path — defends against path-traversal-style names."""
        manifest = SimpleNamespace(features={"weird": object()})
        with (
            patch("attune_author.manifest.load_manifest", return_value=manifest),
            patch("attune_author.manifest.resolve_topic", return_value="../escape"),
            patch("attune_author.manifest.is_safe_feature_name", return_value=False),
        ):
            with pytest.raises(ValueError, match="Invalid feature name"):
                await _exec_author_lookup(
                    {"query": "weird", "help_dir": str(tmp_path / ".help")},
                    ctx,  # type: ignore[arg-type]
                )


# ---------------------------------------------------------------------------
# author.regen — full executor coverage
# ---------------------------------------------------------------------------


class TestAuthorRegen:
    @pytest.mark.asyncio
    async def test_regen_single_feature_succeeds(self, ctx: FakeJobContext, tmp_path: Path) -> None:
        feat = SimpleNamespace(name="auth")
        manifest = SimpleNamespace(features={"auth": feat})
        gen_result = SimpleNamespace(templates=[1, 2])
        with (
            patch("attune_author.manifest.load_manifest", return_value=manifest),
            patch(
                "attune_author.generator.generate_feature_templates",
                return_value=gen_result,
            ),
            patch("attune_gui.routes.rag.invalidate"),
        ):
            out = await _exec_author_regen(
                {
                    "feature": "auth",
                    "project_root": str(tmp_path),
                    "help_dir": str(tmp_path / ".help"),
                },
                ctx,  # type: ignore[arg-type]
            )
        assert len(out["generated"]) == 1
        assert out["generated"][0]["feature"] == "auth"
        assert out["failed"] == []

    @pytest.mark.asyncio
    async def test_regen_unknown_feature_raises_with_available(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        manifest = SimpleNamespace(features={"auth": SimpleNamespace(name="auth")})
        with patch("attune_author.manifest.load_manifest", return_value=manifest):
            with pytest.raises(ValueError, match="ghost.*not in manifest.*auth"):
                await _exec_author_regen(
                    {
                        "feature": "ghost",
                        "project_root": str(tmp_path),
                        "help_dir": str(tmp_path / ".help"),
                    },
                    ctx,  # type: ignore[arg-type]
                )

    @pytest.mark.asyncio
    async def test_regen_no_feature_walks_all(self, ctx: FakeJobContext, tmp_path: Path) -> None:
        feats = {
            "auth": SimpleNamespace(name="auth"),
            "memory": SimpleNamespace(name="memory"),
        }
        manifest = SimpleNamespace(features=feats)
        gen_result = SimpleNamespace(templates=[1])
        with (
            patch("attune_author.manifest.load_manifest", return_value=manifest),
            patch(
                "attune_author.generator.generate_feature_templates",
                return_value=gen_result,
            ),
            patch("attune_gui.routes.rag.invalidate"),
        ):
            out = await _exec_author_regen(
                {
                    "project_root": str(tmp_path),
                    "help_dir": str(tmp_path / ".help"),
                },
                ctx,  # type: ignore[arg-type]
            )
        assert {g["feature"] for g in out["generated"]} == {"auth", "memory"}

    @pytest.mark.asyncio
    async def test_regen_continues_after_per_feature_failure(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        """Per-feature failure must not abort the batch (the BLE001 INTENTIONAL clause)."""
        feats = {
            "auth": SimpleNamespace(name="auth"),
            "broken": SimpleNamespace(name="broken"),
        }
        manifest = SimpleNamespace(features=feats)

        def gen_side_effect(**kwargs):  # type: ignore[no-untyped-def]
            if kwargs["feature"].name == "broken":
                raise RuntimeError("kaboom")
            return SimpleNamespace(templates=[1])

        with (
            patch("attune_author.manifest.load_manifest", return_value=manifest),
            patch(
                "attune_author.generator.generate_feature_templates",
                side_effect=gen_side_effect,
            ),
            patch("attune_gui.routes.rag.invalidate"),
        ):
            out = await _exec_author_regen(
                {
                    "project_root": str(tmp_path),
                    "help_dir": str(tmp_path / ".help"),
                },
                ctx,  # type: ignore[arg-type]
            )
        assert {g["feature"] for g in out["generated"]} == {"auth"}
        assert out["failed"] == ["broken"]


# ---------------------------------------------------------------------------
# author.setup — full executor coverage
# ---------------------------------------------------------------------------


class TestAuthorSetup:
    @pytest.mark.asyncio
    async def test_setup_existing_manifest_skips_init(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        help_dir = tmp_path / ".help"
        help_dir.mkdir()
        (help_dir / "features.yaml").write_text("# manifest")
        feat = SimpleNamespace(name="auth")
        manifest = SimpleNamespace(features={"auth": feat})
        gen_result = SimpleNamespace(templates=[1])
        with (
            patch("attune_author.manifest.load_manifest", return_value=manifest),
            patch(
                "attune_author.generator.generate_feature_templates",
                return_value=gen_result,
            ),
            patch("attune_gui.routes.rag.invalidate"),
        ):
            out = await _exec_author_setup(
                {"project_root": str(tmp_path), "help_dir": str(help_dir)},
                ctx,  # type: ignore[arg-type]
            )
        assert out["features_total"] == 1
        assert any("Manifest exists" in line for line in ctx.lines)

    @pytest.mark.asyncio
    async def test_setup_no_features_returns_early(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        with patch("attune_author.bootstrap.scan_project", return_value=[]):
            out = await _exec_author_setup(
                {"project_root": str(tmp_path), "help_dir": str(tmp_path / ".help")},
                ctx,  # type: ignore[arg-type]
            )
        assert out["discovered"] == 0
        assert "No features" in out["message"]

    @pytest.mark.asyncio
    async def test_setup_full_path_init_and_generate(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        proposals = [SimpleNamespace(name="auth", description="auth feature")]
        feat = SimpleNamespace(name="auth")
        manifest = SimpleNamespace(features={"auth": feat})
        gen_result = SimpleNamespace(templates=[1, 2, 3])
        with (
            patch("attune_author.bootstrap.scan_project", return_value=proposals),
            patch("attune_author.bootstrap.proposals_to_manifest", return_value=manifest),
            patch(
                "attune_author.manifest.save_manifest",
                return_value=tmp_path / ".help" / "features.yaml",
            ),
            patch("attune_author.manifest.load_manifest", return_value=manifest),
            patch(
                "attune_author.generator.generate_feature_templates",
                return_value=gen_result,
            ),
            patch("attune_gui.routes.rag.invalidate"),
        ):
            out = await _exec_author_setup(
                {"project_root": str(tmp_path), "help_dir": str(tmp_path / ".help")},
                ctx,  # type: ignore[arg-type]
            )
        assert out["features_total"] == 1
        assert len(out["generated"]) == 1
        assert out["failed"] == []
