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
    _exec_rag_query,
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
# Help proxies (D3 — executors live in attune_author.orchestration now)
# ---------------------------------------------------------------------------


class TestHelpProxies:
    """Phase D3: ``help.*`` executor bodies moved to attune-author.

    Comprehensive executor tests live in
    ``attune-author/tests/test_orchestration_commands_help.py``. The
    tests here verify the gui-side proxy wiring — registration,
    dispatcher conversion, and metadata mirroring.
    """

    HELP_NAMES = ("help.lookup", "help.search", "help.list")

    def test_three_help_commands_registered(self) -> None:
        for name in self.HELP_NAMES:
            spec = get_command(name)
            assert isinstance(spec, CommandSpec), name
            assert spec.domain == "help"

    def test_proxy_specs_mirror_orchestration_metadata(self) -> None:
        from attune_author.orchestration import COMMANDS as AUTHOR_COMMANDS

        for name in self.HELP_NAMES:
            gui_spec = get_command(name)
            author_spec = AUTHOR_COMMANDS[name]
            assert gui_spec is not None
            assert gui_spec.title == author_spec.title
            assert gui_spec.description == author_spec.description
            assert gui_spec.args_schema == author_spec.args_schema
            assert gui_spec.cancellable == author_spec.cancellable
            assert gui_spec.profiles == author_spec.profiles

    @pytest.mark.asyncio
    async def test_lookup_dispatches_via_run_command(self, ctx: FakeJobContext) -> None:
        from attune_author.orchestration import RunResult

        captured: dict = {}

        async def fake_run_command(name, args, author_ctx):
            captured["name"] = name
            captured["args"] = args
            return RunResult(
                success=True,
                output={"topic": "auth", "content": "body", "total_topics": 5},
                elapsed_ms=1,
            )

        spec = get_command("help.lookup")
        assert spec is not None
        with patch("attune_author.orchestration.run_command", side_effect=fake_run_command):
            out = await spec.executor({"topic": "auth"}, ctx)  # type: ignore[arg-type]

        assert captured["name"] == "help.lookup"
        assert captured["args"] == {"topic": "auth"}
        assert out["topic"] == "auth"

    @pytest.mark.asyncio
    async def test_search_passes_args_through(self, ctx: FakeJobContext) -> None:
        from attune_author.orchestration import RunResult

        captured: dict = {}

        async def fake_run_command(name, args, author_ctx):
            captured["args"] = args
            return RunResult(
                success=True,
                output={"query": "x", "results": [], "count": 0},
                elapsed_ms=1,
            )

        spec = get_command("help.search")
        assert spec is not None
        with patch("attune_author.orchestration.run_command", side_effect=fake_run_command):
            await spec.executor({"query": "x", "limit": 7}, ctx)  # type: ignore[arg-type]

        assert captured["args"] == {"query": "x", "limit": 7}

    @pytest.mark.asyncio
    async def test_list_returns_unwrapped_output(self, ctx: FakeJobContext) -> None:
        from attune_author.orchestration import RunResult

        async def fake_run_command(name, args, author_ctx):
            return RunResult(
                success=True,
                output={"topics": ["a", "b"], "count": 2, "type_filter": None},
                elapsed_ms=1,
            )

        spec = get_command("help.list")
        assert spec is not None
        with patch("attune_author.orchestration.run_command", side_effect=fake_run_command):
            out = await spec.executor({}, ctx)  # type: ignore[arg-type]

        assert out == {"topics": ["a", "b"], "count": 2, "type_filter": None}


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
    async def test_corpus_info_dispatches_to_attune_author(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        # Phase D1: rag.corpus-info now lives in attune_author.orchestration.
        # The gui keeps a thin proxy CommandSpec; this test verifies the
        # dispatcher converts the gui ctx, calls run_command, and returns
        # the unwrapped output dict so the job runner sees a plain payload.
        from attune_author.orchestration import RunResult

        spec = get_command("rag.corpus-info")
        assert spec is not None

        async def fake_run_command(name, args, author_ctx):  # noqa: ARG001
            author_ctx.log("dispatched")
            return RunResult(
                success=True,
                output={"entry_count": 3, "kinds": ["memory", "security"]},
                elapsed_ms=1,
            )

        with patch("attune_author.orchestration.run_command", side_effect=fake_run_command):
            out = await spec.executor(
                {"project_path": str(tmp_path)},
                ctx,  # type: ignore[arg-type]
            )

        assert out == {"entry_count": 3, "kinds": ["memory", "security"]}
        assert "dispatched" in ctx.lines


# ---------------------------------------------------------------------------
# Author proxies (D2 — executors live in attune_author.orchestration now)
# ---------------------------------------------------------------------------


class TestAuthorProxies:
    """Phase D2: ``author.*`` executor bodies moved to attune-author.

    The gui registers thin proxy CommandSpecs via ``_proxy_command`` /
    ``_author_proxy``. These tests verify each proxy is wired correctly
    — registry presence, dispatcher conversion, workspace pre-resolution,
    and the post-dispatch pipeline-cache invalidation. Exhaustive
    behavior tests for the executor bodies live in
    ``attune-author/tests/test_orchestration_commands_author.py``.
    """

    AUTHOR_NAMES = (
        "author.init",
        "author.status",
        "author.maintain",
        "author.lookup",
        "author.regen",
        "author.setup",
    )

    def test_all_six_author_commands_registered(self) -> None:
        for name in self.AUTHOR_NAMES:
            spec = get_command(name)
            assert isinstance(spec, CommandSpec), name
            assert spec.name == name

    def test_proxy_specs_mirror_orchestration_metadata(self) -> None:
        from attune_author.orchestration import COMMANDS as AUTHOR_COMMANDS

        for name in self.AUTHOR_NAMES:
            gui_spec = get_command(name)
            author_spec = AUTHOR_COMMANDS[name]
            assert gui_spec is not None
            assert gui_spec.title == author_spec.title
            assert gui_spec.domain == author_spec.domain
            assert gui_spec.description == author_spec.description
            assert gui_spec.args_schema == author_spec.args_schema
            assert gui_spec.cancellable == author_spec.cancellable
            assert gui_spec.profiles == author_spec.profiles

    @pytest.mark.asyncio
    async def test_init_dispatches_via_run_command(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        from attune_author.orchestration import RunResult

        captured: dict = {}

        async def fake_run_command(name, args, author_ctx):
            captured["name"] = name
            captured["args"] = args
            return RunResult(success=True, output={"already_initialized": True}, elapsed_ms=1)

        spec = get_command("author.init")
        assert spec is not None
        with patch("attune_author.orchestration.run_command", side_effect=fake_run_command):
            out = await spec.executor(
                {"project_root": str(tmp_path)},
                ctx,  # type: ignore[arg-type]
            )

        assert captured["name"] == "author.init"
        assert captured["args"]["project_root"] == str(tmp_path)
        assert out == {"already_initialized": True}

    @pytest.mark.asyncio
    async def test_status_proxy_pre_resolves_workspace(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        """``author.status`` runs with no path → proxy fills from get_workspace."""
        from attune_author.orchestration import RunResult

        captured: dict = {}

        async def fake_run_command(name, args, author_ctx):
            captured["args"] = args
            return RunResult(success=True, output={"total": 0}, elapsed_ms=1)

        spec = get_command("author.status")
        assert spec is not None
        with (
            patch("attune_gui.workspace.get_workspace", return_value=tmp_path),
            patch("attune_author.orchestration.run_command", side_effect=fake_run_command),
        ):
            await spec.executor({}, ctx)  # type: ignore[arg-type]

        # Pre-resolution stuffed explicit absolute paths into args so the
        # orchestration helper accepts them without its own fallback.
        assert "project_root" in captured["args"]
        assert "help_dir" in captured["args"]
        assert Path(captured["args"]["project_root"]) == tmp_path

    @pytest.mark.asyncio
    async def test_regen_proxy_invalidates_pipeline_cache_after_dispatch(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        """``author.regen`` should call rag.invalidate(project_root) after run_command."""
        from attune_author.orchestration import RunResult

        async def fake_run_command(name, args, author_ctx):
            return RunResult(
                success=True,
                output={"generated": [], "failed": [], "project_root": str(tmp_path)},
                elapsed_ms=1,
            )

        spec = get_command("author.regen")
        assert spec is not None

        invalidated: list[Path] = []

        def fake_invalidate(p):
            invalidated.append(p)

        with (
            patch("attune_author.orchestration.run_command", side_effect=fake_run_command),
            patch("attune_gui.routes.rag.invalidate", side_effect=fake_invalidate),
        ):
            out = await spec.executor(
                {"project_path": str(tmp_path)},
                ctx,  # type: ignore[arg-type]
            )

        assert out["generated"] == []
        assert invalidated == [tmp_path]

    @pytest.mark.asyncio
    async def test_setup_proxy_skips_invalidation_when_no_project_root(
        self, ctx: FakeJobContext, tmp_path: Path
    ) -> None:
        """If the executor returns early without project_root, no invalidate call."""
        from attune_author.orchestration import RunResult

        async def fake_run_command(name, args, author_ctx):
            return RunResult(
                success=True, output={"discovered": 0, "message": "empty"}, elapsed_ms=1
            )

        spec = get_command("author.setup")
        assert spec is not None

        invalidated: list[Path] = []

        with (
            patch("attune_author.orchestration.run_command", side_effect=fake_run_command),
            patch(
                "attune_gui.routes.rag.invalidate",
                side_effect=lambda p: invalidated.append(p),
            ),
        ):
            await spec.executor(
                {"project_path": str(tmp_path)},
                ctx,  # type: ignore[arg-type]
            )

        assert invalidated == []
