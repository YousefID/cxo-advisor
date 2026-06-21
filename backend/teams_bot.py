"""Microsoft Teams Bot for ZFP Advisor.

Registers an ActivityHandler that:
  1. Receives a user message from Teams
  2. Detects language (Arabic characters → ar, else en)
  3. Runs the full advisor pipeline (generate_dax → execute_dax → narrate_result)
  4. Sends the answer back with a collapsible DAX code block

POST /api/messages is the Teams Bot Framework webhook endpoint registered
in main.py.

Authentication: The Bot Framework SDK validates the JWT on every incoming
request using MicrosoftAppId + MicrosoftAppPassword from the environment.
"""

from __future__ import annotations

import os
import re

from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import Activity

from backend.advisor import generate_dax, narrate_result
from backend.logging_config import get_logger
from backend.powerbi import execute_dax

logger = get_logger("advisor.teams_bot")

# Arabic Unicode block: U+0600–U+06FF
_AR_PATTERN = re.compile(r"[؀-ۿ]")
_AR_THRESHOLD = 0.10  # >10% Arabic characters → Arabic mode


def _detect_language(text: str) -> str:
    """Return 'ar' if the text is predominantly Arabic, else 'en'."""
    if not text:
        return "en"
    ar_chars = len(_AR_PATTERN.findall(text))
    ratio = ar_chars / len(text)
    return "ar" if ratio > _AR_THRESHOLD else "en"


def _format_teams_response(answer: str, dax_query: str, language: str) -> str:
    """Format the bot reply: answer text + collapsed DAX code block."""
    label = "DAX Query Used" if language == "en" else "استعلام DAX المستخدم"
    return (
        f"{answer}\n\n"
        f"---\n"
        f"**{label}:**\n"
        f"```dax\n{dax_query}\n```"
    )


class ZFPAdvisorBot(ActivityHandler):
    """Teams bot that answers workforce questions using Power BI + Claude."""

    async def on_message_activity(self, turn_context: TurnContext) -> None:
        user_text = (turn_context.activity.text or "").strip()

        if not user_text:
            await turn_context.send_activity(
                Activity(
                    type="message",
                    text=(
                        "Please ask me a question about ZFP workforce data."
                        if True
                        else "يرجى طرح سؤال حول بيانات القوى العاملة."
                    ),
                )
            )
            return

        language = _detect_language(user_text)
        logger.info(
            "teams_message_received",
            extra={"extra": {"language": language, "length": len(user_text)}},
        )

        try:
            dax_query = generate_dax(user_text)
        except Exception as exc:
            logger.error("teams_dax_generation_failed", extra={"extra": {"error": str(exc)}})
            await turn_context.send_activity(
                Activity(
                    type="message",
                    text=_unavailable_msg(language),
                )
            )
            return

        try:
            raw_data = execute_dax(dax_query)
        except Exception as exc:
            logger.error("teams_dax_execution_failed", extra={"extra": {"error": str(exc)}})
            await turn_context.send_activity(
                Activity(
                    type="message",
                    text=_unavailable_msg(language),
                )
            )
            return

        try:
            answer = narrate_result(user_text, dax_query, raw_data, language)
        except Exception as exc:
            logger.error("teams_narration_failed", extra={"extra": {"error": str(exc)}})
            await turn_context.send_activity(
                Activity(
                    type="message",
                    text=_unavailable_msg(language),
                )
            )
            return

        reply_text = _format_teams_response(answer, dax_query, language)
        await turn_context.send_activity(
            Activity(type="message", text=reply_text)
        )
        logger.info(
            "teams_reply_sent",
            extra={"extra": {"language": language, "answer_chars": len(answer)}},
        )


def _unavailable_msg(language: str) -> str:
    if language == "ar":
        return "ZFP Advisor غير متاح مؤقتاً. يرجى المحاولة مرة أخرى لاحقاً."
    return "ZFP Advisor is temporarily unavailable. Please try again in a moment."


def create_bot() -> ZFPAdvisorBot:
    """Factory — called once at app startup."""
    return ZFPAdvisorBot()
