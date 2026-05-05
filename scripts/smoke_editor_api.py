#!/usr/bin/env python3
"""Editor-API smoke script.

Spins up a fresh sidecar against an isolated corpora registry and a
small fixture corpus, then hits every editor endpoint with valid and
invalid inputs, printing a pass/fail table.

Designed for pre-publish gating — exits non-zero on any unexpected
status. Complements the Playwright suite (which covers the UI side):
this one verifies the server contract end-to-end without a browser.

Usage:
    python scripts/smoke_editor_api.py
    python scripts/smoke_editor_api.py --port 8774  # if 8773 is taken

The script picks a random free port if neither --port nor the env var
ATTUNE_SMOKE_PORT is set, so it can run alongside the dev sidecar.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# -- check helpers --------------------------------------------------


@dataclass
class Check:
    name: str
    expected_status: int
    actual_status: int
    detail: str = ""
    body_check: bool = True

    @property
    def passed(self) -> bool:
        return self.actual_status == self.expected_status and self.body_check


@dataclass
class Suite:
    checks: list[Check] = field(default_factory=list)

    def record(self, check: Check) -> None:
        self.checks.append(check)
        glyph = "✓" if check.passed else "✗"
        line = f"  {glyph} [{check.actual_status}] {check.name}"
        if check.detail:
            line += f" — {check.detail}"
        print(line)

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if not c.passed]


# -- sidecar lifecycle ---------------------------------------------


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_ready(url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status < 500:
                    return
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(0.2)
    raise TimeoutError(f"Sidecar didn't become ready at {url} within {timeout}s")


def _start_sidecar(port: int, registry: Path) -> subprocess.Popen[bytes]:
    repo_root = Path(__file__).resolve().parent.parent
    sidecar_dir = repo_root / "sidecar"
    venv_python = repo_root / ".venv" / "bin" / "python"
    if not venv_python.exists():
        raise FileNotFoundError(f"venv python not found at {venv_python}. Run `uv sync` first.")
    env = {
        **os.environ,
        "ATTUNE_CORPORA_REGISTRY": str(registry),
        "ATTUNE_GUI_TEST": "1",
    }
    return subprocess.Popen(
        [str(venv_python), "-m", "attune_gui.main", "--port", str(port)],
        cwd=str(sidecar_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


# -- HTTP helpers ---------------------------------------------------


class Client:
    def __init__(self, base: str) -> None:
        self.base = base
        self.token = ""

    def fetch_token(self) -> None:
        with urllib.request.urlopen(f"{self.base}/api/session/token") as resp:
            self.token = json.loads(resp.read())["token"]

    def get(self, path: str) -> tuple[int, dict[str, Any]]:
        return self._request("GET", path)

    def post(self, path: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        return self._request("POST", path, body)

    def _request(
        self, method: str, path: str, body: dict[str, Any] | None = None
    ) -> tuple[int, dict[str, Any]]:
        url = f"{self.base}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
            req.add_header("X-Attune-Client", self.token)
        try:
            with urllib.request.urlopen(req) as resp:
                payload = resp.read()
                return resp.status, json.loads(payload) if payload else {}
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError:
                parsed = {"_raw": payload.decode("utf-8", "replace")}
            return exc.code, parsed


# -- fixture builder ------------------------------------------------


def _make_corpus(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "concepts").mkdir(exist_ok=True)
    (root / "concepts" / "alpha.md").write_text(
        "---\n"
        "type: concept\n"
        "name: alpha\n"
        "tags: [shared, lonely]\n"
        "aliases: [alf]\n"
        "---\n"
        "Alpha body line.\n",
        encoding="utf-8",
    )
    (root / "concepts" / "beta.md").write_text(
        "---\n"
        "type: concept\n"
        "name: beta\n"
        "tags: [shared]\n"
        "---\n"
        "Beta body — references [[alf]].\n",
        encoding="utf-8",
    )


# -- the smoke ------------------------------------------------------


def smoke(client: Client, corpus_root: Path) -> Suite:
    suite = Suite()
    print("\n[corpus registry]")

    # 1. List corpora — empty.
    status, body = client.get("/api/corpus")
    suite.record(
        Check(
            "GET /api/corpus (empty)",
            200,
            status,
            body_check=isinstance(body, dict)
            and body.get("corpora") == []
            and body.get("active") is None,
        )
    )

    # 2. Register the fixture corpus.
    status, body = client.post(
        "/api/corpus/register",
        {
            "name": "smoke",
            "path": str(corpus_root),
            "kind": "ad-hoc",
        },
    )
    corpus_id = body.get("id", "")
    suite.record(
        Check(
            "POST /api/corpus/register (valid)",
            200,
            status,
            body_check=isinstance(corpus_id, str) and bool(corpus_id),
            detail=f"id={corpus_id}",
        )
    )

    # 3. Register with empty name → 422 (pydantic min_length).
    status, _ = client.post("/api/corpus/register", {"name": "", "path": str(corpus_root)})
    suite.record(Check("POST /api/corpus/register (empty name → 422)", 422, status))

    # 4. List again — has the entry, marked active.
    status, body = client.get("/api/corpus")
    suite.record(
        Check(
            "GET /api/corpus (after register)",
            200,
            status,
            body_check=body.get("active") == corpus_id and len(body.get("corpora", [])) == 1,
        )
    )

    # 5. Resolve a path inside the corpus.
    abs_path = str(corpus_root / "concepts" / "alpha.md")
    status, body = client.post("/api/corpus/resolve", {"abs_path": abs_path})
    suite.record(
        Check(
            "POST /api/corpus/resolve (inside corpus)",
            200,
            status,
            body_check=body.get("corpus_id") == corpus_id
            and body.get("rel_path") == "concepts/alpha.md",
        )
    )

    # 6. Resolve a path outside any registered corpus → 404.
    status, _ = client.post("/api/corpus/resolve", {"abs_path": "/tmp/not/a/corpus.md"})
    suite.record(Check("POST /api/corpus/resolve (outside → 404)", 404, status))

    print("\n[schema]")
    # 7. GET template-schema.
    status, body = client.get("/api/editor/template-schema")
    has_hash_readonly = body.get("properties", {}).get("hash", {}).get("readOnly") is True
    suite.record(
        Check(
            "GET /api/editor/template-schema",
            200,
            status,
            body_check=isinstance(body.get("required"), list) and has_hash_readonly,
            detail="hash.readOnly verified",
        )
    )

    print("\n[template I/O]")
    # 8. GET template (valid).
    status, body = client.get(f"/api/corpus/{corpus_id}/template?path=concepts/alpha.md")
    base_hash = body.get("base_hash", "") if isinstance(body, dict) else ""
    suite.record(
        Check(
            "GET .../template (valid)",
            200,
            status,
            body_check=bool(base_hash) and "alpha" in body.get("text", ""),
        )
    )

    # 9. GET template (path traversal) → 400.
    bad_path = urllib.parse.quote("../../../etc/passwd")
    status, _ = client.get(f"/api/corpus/{corpus_id}/template?path={bad_path}")
    suite.record(Check("GET .../template (traversal → 4xx)", 400, status))

    # 10. GET template (unknown corpus) → 404.
    status, _ = client.get("/api/corpus/no-such-corpus/template?path=concepts/alpha.md")
    suite.record(Check("GET .../template (unknown corpus → 404)", 404, status))

    # 11. POST diff (valid).
    new_text = body.get("text", "") + "\nAppended line.\n" if isinstance(body, dict) else ""
    # Re-read since we shadowed body in step 9/10.
    status, fresh = client.get(f"/api/corpus/{corpus_id}/template?path=concepts/alpha.md")
    base_hash = fresh["base_hash"]
    new_text = fresh["text"] + "\nAppended line.\n"
    status, body = client.post(
        f"/api/corpus/{corpus_id}/template/diff",
        {
            "path": "concepts/alpha.md",
            "draft_text": new_text,
            "base_hash": base_hash,
        },
    )
    hunks = body.get("hunks", []) if isinstance(body, dict) else []
    suite.record(
        Check(
            "POST .../template/diff (valid)",
            200,
            status,
            body_check=len(hunks) >= 1 and all("hunk_id" in h for h in hunks),
        )
    )

    # 12. POST diff (stale base_hash) → 409.
    status, _ = client.post(
        f"/api/corpus/{corpus_id}/template/diff",
        {
            "path": "concepts/alpha.md",
            "draft_text": new_text,
            "base_hash": "deadbeef" * 4,
        },
    )
    suite.record(Check("POST .../template/diff (stale hash → 409)", 409, status))

    # 13. POST save (valid).
    status, body = client.post(
        f"/api/corpus/{corpus_id}/template/save",
        {
            "path": "concepts/alpha.md",
            "draft_text": new_text,
            "base_hash": base_hash,
        },
    )
    suite.record(
        Check(
            "POST .../template/save (valid)",
            200,
            status,
            body_check=isinstance(body, dict) and "new_hash" in body,
        )
    )

    print("\n[lint + autocomplete]")
    # 14. Lint a valid template body.
    status, body = client.post(
        f"/api/corpus/{corpus_id}/lint",
        {
            "path": "concepts/alpha.md",
            "text": new_text,
        },
    )
    suite.record(
        Check(
            "POST .../lint (valid)",
            200,
            status,
            body_check=isinstance(body, list),
        )
    )

    # 15. Lint with broken alias → at least one diagnostic.
    broken = "---\ntype: concept\nname: broken\n---\nReferences [[no-such-alias]] here.\n"
    status, body = client.post(
        f"/api/corpus/{corpus_id}/lint",
        {
            "path": "concepts/alpha.md",
            "text": broken,
        },
    )
    suite.record(
        Check(
            "POST .../lint (broken alias surfaces a diagnostic)",
            200,
            status,
            body_check=any(d.get("code") == "broken-alias" for d in (body or [])),
        )
    )

    # 16. Autocomplete tags.
    status, body = client.get(f"/api/corpus/{corpus_id}/autocomplete?kind=tag&prefix=sh")
    suite.record(
        Check(
            "GET .../autocomplete?kind=tag",
            200,
            status,
            body_check=isinstance(body, list)
            and any(
                (item if isinstance(item, str) else item.get("tag")) == "shared"
                for item in (body or [])
            ),
        )
    )

    # 17. Autocomplete aliases.
    status, body = client.get(f"/api/corpus/{corpus_id}/autocomplete?kind=alias&prefix=alf")
    suite.record(
        Check(
            "GET .../autocomplete?kind=alias",
            200,
            status,
            body_check=isinstance(body, list) and len(body) >= 1,
        )
    )

    # 18. Autocomplete with bogus kind → 422.
    status, _ = client.get(f"/api/corpus/{corpus_id}/autocomplete?kind=bogus&prefix=x")
    suite.record(Check("GET .../autocomplete (bogus kind → 422)", 422, status))

    print("\n[refactor]")
    # 19. Rename preview (alias).
    status, body = client.post(
        f"/api/corpus/{corpus_id}/refactor/rename/preview",
        {
            "old": "alf",
            "new": "alpha-renamed",
            "kind": "alias",
        },
    )
    suite.record(
        Check(
            "POST .../rename/preview (alias)",
            200,
            status,
            body_check=isinstance(body.get("edits"), list),
        )
    )

    # 20. Rename preview collision.
    status, body = client.post(
        f"/api/corpus/{corpus_id}/refactor/rename/preview",
        {
            "old": "alf",
            "new": "alf",
            "kind": "alias",
        },
    )
    # Same name → no-op plan with empty edits, NOT an error.
    suite.record(
        Check(
            "POST .../rename/preview (same name → empty plan)",
            200,
            status,
            body_check=body.get("edits") == [],
        )
    )

    # 21. Rename preview template_path → 400 (NotImplementedError).
    status, _ = client.post(
        f"/api/corpus/{corpus_id}/refactor/rename/preview",
        {
            "old": "alpha.md",
            "new": "alpha2.md",
            "kind": "template_path",
        },
    )
    suite.record(Check("POST .../rename/preview (template_path → 400)", 400, status))

    # 22. Rename apply (alias) — actually rewrites files.
    status, body = client.post(
        f"/api/corpus/{corpus_id}/refactor/rename/apply",
        {
            "old": "alf",
            "new": "alpha-renamed",
            "kind": "alias",
        },
    )
    suite.record(
        Check(
            "POST .../rename/apply (alias)",
            200,
            status,
            body_check=isinstance(body.get("affected_files"), list)
            and len(body["affected_files"]) >= 1,
        )
    )

    # 23. Set the active corpus (back to itself — no-op-ish but valid).
    status, body = client.post("/api/corpus/active", {"id": corpus_id})
    suite.record(
        Check(
            "POST /api/corpus/active",
            200,
            status,
            body_check=body.get("id") == corpus_id,
        )
    )

    # 24. Set active to nonexistent id → 404.
    status, _ = client.post("/api/corpus/active", {"id": "no-such-corpus"})
    suite.record(Check("POST /api/corpus/active (unknown → 404)", 404, status))

    print("\n[health]")
    # 25. Healthz with valid token.
    status, body = client.get(f"/healthz?token={urllib.parse.quote(client.token)}")
    suite.record(
        Check(
            "GET /healthz?token=<valid>",
            200,
            status,
            body_check=body.get("status") == "ok",
        )
    )

    # 26. Healthz with bogus token → 401.
    status, _ = client.get("/healthz?token=wrong")
    suite.record(Check("GET /healthz?token=<wrong> (→ 401)", 401, status))

    # 27. Healthz without token → 422.
    status, _ = client.get("/healthz")
    suite.record(Check("GET /healthz (no token → 422)", 422, status))

    return suite


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    port = args.port or int(os.environ.get("ATTUNE_SMOKE_PORT", "0")) or _free_port()
    base = f"http://127.0.0.1:{port}"

    tmp = Path(tempfile.mkdtemp(prefix="attune-smoke-"))
    registry = tmp / "corpora.json"
    corpus_root = tmp / "corpus"
    _make_corpus(corpus_root)

    print(f"Sidecar @ {base}; registry @ {registry}; corpus @ {corpus_root}")
    proc = _start_sidecar(port, registry)
    try:
        _wait_ready(f"{base}/editor")
        client = Client(base)
        client.fetch_token()
        print(f"Session token: {client.token[:8]}…")
        suite = smoke(client, corpus_root)

        print("\n" + "─" * 60)
        passed = len(suite.checks) - len(suite.failed)
        print(f"{passed}/{len(suite.checks)} checks passed")
        if suite.failed:
            print("FAILED:")
            for c in suite.failed:
                print(f"  ✗ {c.name} — got {c.actual_status}, expected {c.expected_status}")
            return 1
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
