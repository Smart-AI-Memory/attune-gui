"""Smoke tests for system routes — no external deps required."""

from __future__ import annotations

from attune_gui.app import create_app
from fastapi.testclient import TestClient


def test_health_ok():
    client = TestClient(create_app())
    r = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "." in body["version"]
    assert "." in body["python"]


def test_session_token_is_stable():
    client = TestClient(create_app())
    hdrs = {"Origin": "http://127.0.0.1:3000"}
    r1 = client.get("/api/session/token", headers=hdrs).json()
    r2 = client.get("/api/session/token", headers=hdrs).json()
    assert r1["token"] == r2["token"]
    assert len(r1["token"]) >= 32


def test_bad_origin_rejected():
    client = TestClient(create_app())
    r = client.get("/api/health", headers={"Origin": "https://evil.example.com"})
    assert r.status_code == 403


def test_no_origin_allowed():
    # curl / server-to-server calls have no Origin; localhost binding is the real guard.
    client = TestClient(create_app())
    r = client.get("/api/health")
    assert r.status_code == 200


def test_mutating_requires_client_token():
    # Hitting /api/rag/query without X-Attune-Client should 403.
    client = TestClient(create_app())
    r = client.post(
        "/api/rag/query",
        json={"query": "hello"},
        headers={"Origin": "http://localhost:5173"},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "invalid_client"
