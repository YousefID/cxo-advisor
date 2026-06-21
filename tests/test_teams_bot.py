"""Tests for backend/teams_bot.py — Teams bot message handling."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key")
os.environ.setdefault("POWERBI_WORKSPACE_ID", "ws-test")
os.environ.setdefault("POWERBI_DATASET_ID", "ds-test")
os.environ.setdefault("POWERBI_TENANT_ID", "tenant-test")
os.environ.setdefault("POWERBI_CLIENT_ID", "client-test")
os.environ.setdefault("POWERBI_CLIENT_SECRET", "secret-test")

# ── Language detection ────────────────────────────────────────────────────────

def test_detect_language_english():
    from backend.teams_bot import _detect_language
    assert _detect_language("What is our billable utilization this month?") == "en"


def test_detect_language_arabic():
    from backend.teams_bot import _detect_language
    assert _detect_language("ما نسبة الاستخدام القابل للفوترة هذا الشهر؟") == "ar"


def test_detect_language_mixed_mostly_en():
    from backend.teams_bot import _detect_language
    # Long English sentence with a single Arabic word — Arabic ratio <10%
    assert _detect_language("Show me the latest workforce report for the مشروع project in detail") == "en"


def test_detect_language_empty_string():
    from backend.teams_bot import _detect_language
    assert _detect_language("") == "en"


def test_detect_language_arabic_only_characters():
    from backend.teams_bot import _detect_language
    # Pure Arabic
    assert _detect_language("السلام عليكم كيف حالك") == "ar"


# ── Format Teams response ─────────────────────────────────────────────────────

def test_format_teams_response_english():
    from backend.teams_bot import _format_teams_response
    result = _format_teams_response("Design BU leads.", "EVALUATE ...", "en")
    assert "Design BU leads." in result
    assert "DAX Query Used" in result
    assert "```dax" in result
    assert "EVALUATE ..." in result


def test_format_teams_response_arabic():
    from backend.teams_bot import _format_teams_response
    result = _format_teams_response("وحدة التصميم في المقدمة.", "EVALUATE ...", "ar")
    assert "وحدة التصميم" in result
    assert "استعلام DAX المستخدم" in result


def test_format_teams_response_contains_separator():
    from backend.teams_bot import _format_teams_response
    result = _format_teams_response("Answer", "DAX_QUERY", "en")
    assert "---" in result


# ── Bot message handling ──────────────────────────────────────────────────────

def _make_turn_context(text: str) -> MagicMock:
    ctx = MagicMock()
    ctx.activity = MagicMock()
    ctx.activity.text = text
    ctx.send_activity = AsyncMock()
    return ctx


@pytest.mark.asyncio
async def test_bot_sends_reply_on_english_question():
    from backend.teams_bot import ZFPAdvisorBot

    bot = ZFPAdvisorBot()
    ctx = _make_turn_context("Which business unit has the most overtime?")

    with (
        patch("backend.teams_bot.generate_dax", return_value="EVALUATE ..."),
        patch("backend.teams_bot.execute_dax", return_value='[{"BU": "Design", "Hours": 100}]'),
        patch("backend.teams_bot.narrate_result", return_value="Design BU leads with 100 hours."),
    ):
        await bot.on_message_activity(ctx)

    ctx.send_activity.assert_called_once()
    call_args = ctx.send_activity.call_args[0][0]
    assert "Design BU leads" in call_args.text


@pytest.mark.asyncio
async def test_bot_sends_reply_on_arabic_question():
    from backend.teams_bot import ZFPAdvisorBot

    bot = ZFPAdvisorBot()
    ctx = _make_turn_context("ما نسبة الاستخدام القابل للفوترة هذا الشهر؟")

    with (
        patch("backend.teams_bot.generate_dax", return_value="EVALUATE ..."),
        patch("backend.teams_bot.execute_dax", return_value='[{"util": 0.72}]'),
        patch("backend.teams_bot.narrate_result", return_value="نسبة الاستخدام 72٪."),
    ):
        await bot.on_message_activity(ctx)

    ctx.send_activity.assert_called_once()
    call_args = ctx.send_activity.call_args[0][0]
    assert "72" in call_args.text or "نسبة" in call_args.text


@pytest.mark.asyncio
async def test_bot_handles_empty_message():
    from backend.teams_bot import ZFPAdvisorBot

    bot = ZFPAdvisorBot()
    ctx = _make_turn_context("")

    await bot.on_message_activity(ctx)

    ctx.send_activity.assert_called_once()
    call_text = ctx.send_activity.call_args[0][0].text
    assert "question" in call_text.lower() or "يرجى" in call_text


@pytest.mark.asyncio
async def test_bot_handles_whitespace_only_message():
    from backend.teams_bot import ZFPAdvisorBot

    bot = ZFPAdvisorBot()
    ctx = _make_turn_context("   \n\t  ")

    await bot.on_message_activity(ctx)

    ctx.send_activity.assert_called_once()


@pytest.mark.asyncio
async def test_bot_returns_unavailable_on_dax_gen_failure():
    from backend.teams_bot import ZFPAdvisorBot

    bot = ZFPAdvisorBot()
    ctx = _make_turn_context("Show me hours")

    with patch("backend.teams_bot.generate_dax", side_effect=Exception("Claude API down")):
        await bot.on_message_activity(ctx)

    call_text = ctx.send_activity.call_args[0][0].text
    assert "unavailable" in call_text.lower() or "temporarily" in call_text.lower()


@pytest.mark.asyncio
async def test_bot_returns_unavailable_on_powerbi_failure():
    from backend.teams_bot import ZFPAdvisorBot

    bot = ZFPAdvisorBot()
    ctx = _make_turn_context("Show me hours")

    with (
        patch("backend.teams_bot.generate_dax", return_value="EVALUATE ..."),
        patch("backend.teams_bot.execute_dax", side_effect=Exception("Power BI down")),
    ):
        await bot.on_message_activity(ctx)

    call_text = ctx.send_activity.call_args[0][0].text
    assert "unavailable" in call_text.lower()


@pytest.mark.asyncio
async def test_bot_returns_unavailable_on_narration_failure():
    from backend.teams_bot import ZFPAdvisorBot

    bot = ZFPAdvisorBot()
    ctx = _make_turn_context("Show me hours")

    with (
        patch("backend.teams_bot.generate_dax", return_value="EVALUATE ..."),
        patch("backend.teams_bot.execute_dax", return_value='[{"Hours": 100}]'),
        patch("backend.teams_bot.narrate_result", side_effect=Exception("Claude narration failed")),
    ):
        await bot.on_message_activity(ctx)

    call_text = ctx.send_activity.call_args[0][0].text
    assert "unavailable" in call_text.lower()


# ── Unavailable message helper ────────────────────────────────────────────────

def test_unavailable_msg_english():
    from backend.teams_bot import _unavailable_msg
    msg = _unavailable_msg("en")
    assert "ZFP Advisor" in msg
    assert "temporarily" in msg


def test_unavailable_msg_arabic():
    from backend.teams_bot import _unavailable_msg
    msg = _unavailable_msg("ar")
    assert "ZFP Advisor" in msg
    assert "غير متاح" in msg


# ── create_bot factory ────────────────────────────────────────────────────────

def test_create_bot_returns_instance():
    from backend.teams_bot import ZFPAdvisorBot, create_bot
    bot = create_bot()
    assert isinstance(bot, ZFPAdvisorBot)
