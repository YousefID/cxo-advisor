"""Tests for backend/auth.py — Power BI service principal authentication."""

from __future__ import annotations

import os
import time
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("POWERBI_TENANT_ID", "a7f6706f-2e5e-4273-9614-efeec6968702")
os.environ.setdefault("POWERBI_CLIENT_ID", "test-client-id")
os.environ.setdefault("POWERBI_CLIENT_SECRET", "test-secret")
os.environ.setdefault("POWERBI_WORKSPACE_ID", "ws-test")
os.environ.setdefault("POWERBI_DATASET_ID", "ds-test")


def _mock_msal_app(access_token: str, expires_in: int = 3600):
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {
        "access_token": access_token,
        "expires_in": expires_in,
    }
    return mock_app


def _mock_msal_fail(error_description: str):
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {
        "error": "invalid_client",
        "error_description": error_description,
    }
    return mock_app


# ── Success paths ─────────────────────────────────────────────────────────────

def test_get_access_token_success():
    from backend import auth
    auth.clear_token_cache()

    mock_app = _mock_msal_app("tok-abc")
    with patch("msal.ConfidentialClientApplication", return_value=mock_app):
        token = auth.get_access_token()

    assert token == "tok-abc"


def test_token_is_cached_after_first_call():
    from backend import auth
    auth.clear_token_cache()

    mock_app = _mock_msal_app("tok-cached")
    with patch("msal.ConfidentialClientApplication", return_value=mock_app):
        t1 = auth.get_access_token()
        t2 = auth.get_access_token()

    assert t1 == t2 == "tok-cached"
    assert mock_app.acquire_token_for_client.call_count == 1


def test_expired_token_refreshes():
    from backend import auth
    auth.clear_token_cache()

    mock_app = _mock_msal_app("tok-new")
    with patch("msal.ConfidentialClientApplication", return_value=mock_app):
        # Plant an expired token
        auth._cache["token"] = "tok-old"
        auth._cache["expires_at"] = time.time() - 10  # already expired

        token = auth.get_access_token()

    assert token == "tok-new"


def test_token_refreshes_when_near_expiry():
    from backend import auth
    auth.clear_token_cache()

    mock_app = _mock_msal_app("tok-refreshed")
    with patch("msal.ConfidentialClientApplication", return_value=mock_app):
        # Plant a token expiring in 30 seconds (< 60s threshold)
        auth._cache["token"] = "tok-expiring-soon"
        auth._cache["expires_at"] = time.time() + 30

        token = auth.get_access_token()

    assert token == "tok-refreshed"


# ── Failure paths ─────────────────────────────────────────────────────────────

def test_auth_failure_raises_runtime_error():
    from backend import auth
    auth.clear_token_cache()

    mock_app = _mock_msal_fail("AADSTS70011: Invalid credentials")
    with patch("msal.ConfidentialClientApplication", return_value=mock_app):
        with pytest.raises(RuntimeError, match="Power BI authentication failed"):
            auth.get_access_token()


def test_missing_client_id_raises():
    from backend import auth
    auth.clear_token_cache()

    with patch.dict(os.environ, {"POWERBI_CLIENT_ID": ""}):
        with pytest.raises(RuntimeError, match="POWERBI_CLIENT_ID"):
            auth.get_access_token()


def test_missing_client_secret_raises():
    from backend import auth
    auth.clear_token_cache()

    with patch.dict(os.environ, {"POWERBI_CLIENT_SECRET": ""}):
        with pytest.raises(RuntimeError, match="POWERBI_CLIENT_SECRET"):
            auth.get_access_token()


def test_missing_tenant_id_raises():
    from backend import auth
    auth.clear_token_cache()

    with patch.dict(os.environ, {"POWERBI_TENANT_ID": ""}):
        with pytest.raises(RuntimeError, match="POWERBI_TENANT_ID"):
            auth.get_access_token()


# ── clear_token_cache ─────────────────────────────────────────────────────────

def test_clear_token_cache_removes_cached_token():
    from backend import auth

    mock_app = _mock_msal_app("tok-first")
    with patch("msal.ConfidentialClientApplication", return_value=mock_app):
        auth.get_access_token()

    auth.clear_token_cache()
    assert auth._cache == {}
