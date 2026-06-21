"""Tests for backend/main.py — FastAPI endpoint integration tests."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Set env before importing the app
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key")
os.environ.setdefault("POWERBI_WORKSPACE_ID", "ws-test")
os.environ.setdefault("POWERBI_DATASET_ID", "ds-test")
os.environ.setdefault("POWERBI_TENANT_ID", "tenant-test")
os.environ.setdefault("POWERBI_CLIENT_ID", "client-test")
os.environ.setdefault("POWERBI_CLIENT_SECRET", "secret-test")
os.environ.setdefault("MicrosoftAppId", "")
os.environ.setdefault("MicrosoftAppPassword", "")


@pytest.fixture(scope="module")
def client():
    from backend.main import app
    return TestClient(app)


# ── GET / ─────────────────────────────────────────────────────────────────────

def test_root_returns_html_or_json(client):
    resp = client.get("/")
    assert resp.status_code == 200
    # Either serves index.html (HTML) or JSON fallback
    assert resp.headers["content-type"].startswith(("text/html", "application/json"))


# ── GET /health ───────────────────────────────────────────────────────────────

def test_health_endpoint_returns_ok_structure(client):
    with patch("backend.auth.get_access_token", side_effect=Exception("auth off")):
        resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] == "ok"
    assert "powerbi" in data
    assert "claude" in data


def test_health_powerbi_connected_when_auth_succeeds(client):
    with patch("backend.auth.get_access_token", return_value="tok"):
        resp = client.get("/health")
    data = resp.json()
    assert data["powerbi"] == "connected"


def test_health_powerbi_error_when_auth_fails(client):
    with patch("backend.auth.get_access_token", side_effect=RuntimeError("creds bad")):
        resp = client.get("/health")
    data = resp.json()
    assert data["powerbi"] == "error"


def test_health_claude_error_without_api_key(client):
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
        resp = client.get("/health")
    data = resp.json()
    assert data["claude"] == "error"


# ── GET /debug ────────────────────────────────────────────────────────────────

def test_debug_endpoint_returns_json(client):
    with (
        patch("backend.auth.get_access_token", side_effect=RuntimeError("no creds")),
    ):
        resp = client.get("/debug")
    assert resp.status_code == 200
    data = resp.json()
    assert "timestamp" in data
    assert "claude" in data
    assert "powerbi_auth" in data
    assert "powerbi_query" in data
    assert "overall" in data


def test_debug_powerbi_query_skipped_when_auth_fails(client):
    with patch("backend.auth.get_access_token", side_effect=RuntimeError("no creds")):
        resp = client.get("/debug")
    data = resp.json()
    assert data["powerbi_auth"]["status"] == "error"
    assert data["powerbi_query"]["status"] == "skipped"


# ── POST /ask ─────────────────────────────────────────────────────────────────

def test_ask_success_english(client):
    with (
        patch("backend.advisor.generate_dax", return_value="EVALUATE TOP 10 ..."),
        patch("backend.powerbi.execute_dax", return_value='[{"BU": "Design", "Hours": 500}]'),
        patch("backend.advisor.narrate_result", return_value="Design BU leads with 500 hours."),
    ):
        resp = client.post("/ask", json={"question": "Which BU has most hours?", "language": "en"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "Design" in data["answer"]
    assert data["dax_query"] == "EVALUATE TOP 10 ..."


def test_ask_success_arabic(client):
    with (
        patch("backend.advisor.generate_dax", return_value="EVALUATE ..."),
        patch("backend.powerbi.execute_dax", return_value='[{"Hours": 100}]'),
        patch("backend.advisor.narrate_result", return_value="النتيجة 100 ساعة."),
    ):
        resp = client.post(
            "/ask",
            json={"question": "ما مجموع الساعات؟", "language": "ar"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "ساعة" in data["answer"]


def test_ask_returns_error_when_dax_gen_fails(client):
    with patch("backend.advisor.generate_dax", side_effect=Exception("Claude API down")):
        resp = client.post("/ask", json={"question": "Any question?", "language": "en"})

    assert resp.status_code == 200  # Returns 200 with error in body
    data = resp.json()
    assert data["status"] == "error"
    assert "unavailable" in data["answer"].lower()


def test_ask_returns_error_when_powerbi_fails(client):
    with (
        patch("backend.advisor.generate_dax", return_value="EVALUATE ..."),
        patch("backend.powerbi.execute_dax", side_effect=Exception("Power BI down")),
    ):
        resp = client.post("/ask", json={"question": "Any question?", "language": "en"})

    data = resp.json()
    assert data["status"] == "error"


def test_ask_returns_error_when_powerbi_returns_error_string(client):
    with (
        patch("backend.advisor.generate_dax", return_value="EVALUATE ..."),
        patch("backend.powerbi.execute_dax", return_value="Power BI API error 403: Forbidden"),
    ):
        resp = client.post("/ask", json={"question": "Any question?", "language": "en"})

    data = resp.json()
    assert data["status"] == "error"


def test_ask_validates_empty_question(client):
    resp = client.post("/ask", json={"question": "", "language": "en"})
    assert resp.status_code == 422  # Pydantic validation error


def test_ask_validates_invalid_language(client):
    resp = client.post(
        "/ask",
        json={"question": "test", "language": "fr"},  # only en/ar allowed
    )
    assert resp.status_code == 422


def test_ask_default_language_is_en(client):
    with (
        patch("backend.advisor.generate_dax", return_value="EVALUATE ..."),
        patch("backend.powerbi.execute_dax", return_value='[{"x": 1}]'),
        patch("backend.advisor.narrate_result", return_value="Answer.") as mock_narrate,
    ):
        client.post("/ask", json={"question": "test question"})
        call_kwargs = mock_narrate.call_args
        assert call_kwargs[0][3] == "en" or call_kwargs.args[3] == "en"


# ── POST /api/messages (Teams) ────────────────────────────────────────────────

def test_api_messages_returns_503_when_teams_not_configured(client):
    # MicrosoftAppId/Password are empty strings → Teams disabled
    resp = client.post("/api/messages", json={"type": "message", "text": "hi"})
    assert resp.status_code == 503
    data = resp.json()
    assert "not configured" in data["error"].lower()
