"""Tests for backend/powerbi.py — DAX execution against Power BI API."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key")
os.environ.setdefault("POWERBI_WORKSPACE_ID", "ws-test-id")
os.environ.setdefault("POWERBI_DATASET_ID", "ds-test-id")
os.environ.setdefault("POWERBI_TENANT_ID", "tenant-test")
os.environ.setdefault("POWERBI_CLIENT_ID", "client-test")
os.environ.setdefault("POWERBI_CLIENT_SECRET", "secret-test")


def _mock_token():
    return patch("backend.powerbi.get_access_token", return_value="fake-bearer-token")


def _mock_http_response(status_code=200, json_data=None, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    return resp


# ── Successful queries ────────────────────────────────────────────────────────

def test_execute_dax_returns_rows_as_json():
    from backend.powerbi import execute_dax

    rows = [{"BU": "Design", "Hours": 100.0}]
    api_resp = {"results": [{"tables": [{"rows": rows}]}]}
    mock_resp = _mock_http_response(200, api_resp)

    with _mock_token(), patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.post.return_value = mock_resp
        result = execute_dax("EVALUATE SUMMARIZECOLUMNS(TS_DTL[BUSNS_UNIT_NO])")

    parsed = json.loads(result)
    assert parsed[0]["BU"] == "Design"
    assert parsed[0]["Hours"] == 100.0


def test_execute_dax_multiple_rows():
    from backend.powerbi import execute_dax

    rows = [{"BU": f"Unit{i}", "Hours": i * 10} for i in range(5)]
    api_resp = {"results": [{"tables": [{"rows": rows}]}]}
    mock_resp = _mock_http_response(200, api_resp)

    with _mock_token(), patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.post.return_value = mock_resp
        result = execute_dax("EVALUATE SOMETHING")

    parsed = json.loads(result)
    assert len(parsed) == 5


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_execute_dax_empty_rows():
    from backend.powerbi import execute_dax

    api_resp = {"results": [{"tables": [{"rows": []}]}]}
    mock_resp = _mock_http_response(200, api_resp)

    with _mock_token(), patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.post.return_value = mock_resp
        result = execute_dax("EVALUATE SOMETHING")

    assert result == "No data found for this query"


def test_execute_dax_missing_results_key():
    from backend.powerbi import execute_dax

    mock_resp = _mock_http_response(200, {})

    with _mock_token(), patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.post.return_value = mock_resp
        result = execute_dax("EVALUATE SOMETHING")

    assert result == "No data found for this query"


# ── Error handling ────────────────────────────────────────────────────────────

def test_execute_dax_api_error_400():
    from backend.powerbi import execute_dax

    mock_resp = _mock_http_response(400, text="Bad Request — invalid DAX")

    with _mock_token(), patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.post.return_value = mock_resp
        result = execute_dax("EVALUATE INVALID_QUERY")

    assert "Power BI API error 400" in result


def test_execute_dax_api_error_403():
    from backend.powerbi import execute_dax

    mock_resp = _mock_http_response(403, text="Forbidden")

    with _mock_token(), patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.post.return_value = mock_resp
        result = execute_dax("EVALUATE SOMETHING")

    assert "403" in result


def test_execute_dax_timeout():
    from backend.powerbi import execute_dax

    with _mock_token(), patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.post.side_effect = (
            httpx.TimeoutException("Request timed out")
        )
        result = execute_dax("EVALUATE SOMETHING")

    assert "timed out" in result.lower()


def test_execute_dax_connection_error():
    from backend.powerbi import execute_dax

    with _mock_token(), patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.post.side_effect = (
            httpx.ConnectError("Connection refused")
        )
        result = execute_dax("EVALUATE SOMETHING")

    assert "Unable to connect" in result or "connect" in result.lower()


def test_execute_dax_missing_env_vars():
    from backend.powerbi import execute_dax

    with _mock_token():
        with patch.dict(os.environ, {"POWERBI_WORKSPACE_ID": "", "POWERBI_DATASET_ID": ""}):
            result = execute_dax("EVALUATE SOMETHING")

    assert "not configured" in result


# ── Auth headers ──────────────────────────────────────────────────────────────

def test_execute_dax_sends_bearer_token():
    from backend.powerbi import execute_dax

    rows = [{"x": 1}]
    api_resp = {"results": [{"tables": [{"rows": rows}]}]}
    mock_resp = _mock_http_response(200, api_resp)
    mock_post = MagicMock(return_value=mock_resp)

    with _mock_token(), patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.post = mock_post
        execute_dax("EVALUATE SOMETHING")

    call_kwargs = mock_post.call_args[1]
    assert call_kwargs["headers"]["Authorization"] == "Bearer fake-bearer-token"
