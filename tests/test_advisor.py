"""Tests for backend/advisor.py — DAX generation and result narration."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

# Minimal env so imports don't fail
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key")
os.environ.setdefault("POWERBI_WORKSPACE_ID", "ws-test")
os.environ.setdefault("POWERBI_DATASET_ID", "ds-test")
os.environ.setdefault("POWERBI_TENANT_ID", "tenant-test")
os.environ.setdefault("POWERBI_CLIENT_ID", "client-test")
os.environ.setdefault("POWERBI_CLIENT_SECRET", "secret-test")


def _mock_claude(response_text: str):
    """Patch _get_client to return a mock that yields `response_text`."""
    msg = MagicMock()
    msg.content = [MagicMock(text=response_text)]
    client = MagicMock()
    client.messages.create.return_value = msg
    return patch("backend.advisor._get_client", return_value=client)


# ── generate_dax ──────────────────────────────────────────────────────────────

def test_generate_dax_returns_evaluate_query():
    from backend.advisor import generate_dax

    dax = "EVALUATE SUMMARIZECOLUMNS(TS_DTL[BUSNS_UNIT_NO], \"Hours\", SUM(TS_DTL[RGLR_HRS]))"
    with _mock_claude(dax):
        result = generate_dax("Which business unit has the most hours?")

    assert result.startswith("EVALUATE")


def test_generate_dax_strips_whitespace():
    from backend.advisor import generate_dax

    with _mock_claude("  EVALUATE SOMETHING  "):
        result = generate_dax("test question")

    assert result == "EVALUATE SOMETHING"


def test_generate_dax_passes_question_to_claude():
    from backend.advisor import generate_dax

    with _mock_claude("EVALUATE ROW(\"n\", 1)") as mock_get:
        generate_dax("How many Saudi employees this month?")
        call = mock_get.return_value.messages.create.call_args
        content = call[1]["messages"][0]["content"]
        assert "Saudi" in content


def test_generate_dax_uses_correct_model():
    from backend.advisor import generate_dax

    with _mock_claude("EVALUATE THING") as mock_get:
        generate_dax("test")
        call = mock_get.return_value.messages.create.call_args
        model = call[1]["model"]
        assert "claude" in model.lower()


# ── narrate_result ────────────────────────────────────────────────────────────

def test_narrate_result_english():
    from backend.advisor import narrate_result

    narrative = "Design BU logged 1,200 hours this month, up 8% from last month."
    with _mock_claude(narrative):
        result = narrate_result(
            "Which BU has most hours?",
            "EVALUATE ...",
            '[{"BU": "Design", "Hours": 1200}]',
            "en",
        )

    assert len(result) > 0
    assert "Design" in result or "1,200" in result or result == narrative


def test_narrate_result_arabic():
    from backend.advisor import narrate_result

    narrative = "سجّلت وحدة التصميم 1200 ساعة هذا الشهر."
    with _mock_claude(narrative) as mock_get:
        result = narrate_result(
            "أي وحدة لديها أكثر الساعات؟",
            "EVALUATE ...",
            '[{"BU": "Design", "Hours": 1200}]',
            "ar",
        )
        call = mock_get.return_value.messages.create.call_args
        system_prompt = call[1].get("system", "")
        assert "Arabic" in system_prompt

    assert len(result) > 0


def test_narrate_result_strips_response():
    from backend.advisor import narrate_result

    with _mock_claude("  Answer with spaces  "):
        result = narrate_result("q", "dax", "data", "en")

    assert result == "Answer with spaces"


def test_narrate_result_includes_question_in_prompt():
    from backend.advisor import narrate_result

    with _mock_claude("answer") as mock_get:
        narrate_result("overtime question", "EVALUATE ...", "[]", "en")
        call = mock_get.return_value.messages.create.call_args
        user_content = call[1]["messages"][0]["content"]
        assert "overtime question" in user_content


def test_get_client_raises_without_api_key():
    from backend import advisor
    original_client = advisor._client
    advisor._client = None  # force re-init
    try:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
            os.environ["ANTHROPIC_API_KEY"] = ""
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                advisor._get_client()
    finally:
        advisor._client = original_client
