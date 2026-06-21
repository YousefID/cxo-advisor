"""ZFP Advisor AI layer — DAX generation and result narration.

Two public functions:
  generate_dax(question) → DAX query string
  narrate_result(question, dax, data, language) → business narrative string

Both use the Anthropic Claude API (claude-sonnet-4-5).
Data classification: Internal — aggregate workforce data only, no PII.
"""

from __future__ import annotations

import os

import anthropic

from backend.logging_config import get_logger

logger = get_logger("advisor.claude")

_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")

_DAX_SYSTEM = """You are a DAX query generator for Power BI. Generate ONLY valid DAX queries.
Start every query with EVALUATE. Return ONLY the DAX query, nothing else.
No explanation, no markdown, no backticks.

PRIMARY TABLE: TS_DTL (Timesheet Detail)
Columns: EMP_NO, WEEK_NO (YYYYWW integer, current week = MAX),
TS_DATE (date), RGLR_HRS (decimal), OT_HRS (decimal),
PROJECT_NO (text, blank = overhead/non-billable),
Project_Name (text), BUSNS_UNIT_NO (text),
NATIONALITY_NO (text, "1" = Saudi), TD_ID,
DEPT_NO, BRANCH_NO

RELATED TABLES (use RELATED() to join):
- EMPLOYEES: EMP_NO → employee details, DEPT_NO, BRANCH_NO, BUSNS_UNIT_NO
- BUSNS_UNIT: BUSNS_UNIT_NO → "Clean Name" column for BU display name
- DEPARTMENT: DEPT_NO → DEPT_DSCR
- NATIONS: NATIONALITY_NO → COUNTRY_NAME
- BRANCH: BRANCH_NO → BRANCH_NAME
- PROJECTS: PROJECT_NO → project details, STATUS, BUSNS_SECTOR
- STATUS: → STATUS_DSCR
- BUSNS_SECTOR: → SECTOR_DSCR

BILLABLE LOGIC: PROJECT_NO is NOT blank = billable hours
OVERHEAD LOGIC: PROJECT_NO IS blank = non-billable/overhead hours

WEEK NUMBER FORMAT: YYYYWW (e.g. 202523 = week 23 of 2025)
Current year is 2026.

COMMON PATTERNS:
- Total hours = SUM(TS_DTL[RGLR_HRS]) + SUM(TS_DTL[OT_HRS])
- Billable hours = CALCULATE(SUM(TS_DTL[RGLR_HRS]), TS_DTL[PROJECT_NO] <> "")
- Utilization % = DIVIDE(billable hours, total hours, 0)
- Current month filter = MONTH(TS_DTL[TS_DATE]) = MONTH(TODAY()) && YEAR(TS_DTL[TS_DATE]) = YEAR(TODAY())
- Saudi employees = CALCULATE(..., TS_DTL[NATIONALITY_NO] = "1")

Always use SUMMARIZECOLUMNS for grouped results.
Always include a readable label column alongside numeric columns.
Limit results to TOP 10 unless user asks for all."""

_NARRATION_SYSTEM = """You are ZFP Advisor, an AI business advisor for senior leadership of ZFP Group,
an Architecture & Engineering firm operating in Saudi Arabia and Egypt.

Your job: interpret Power BI data and deliver a clear, confident business answer.

Rules:
- Lead with the key number or finding
- Follow with one comparison (vs last month or last week if data allows)
- Add one business insight (what this means)
- Suggest one action if relevant
- Maximum 120 words
- Use SAR for costs
- Never say "the data shows" — just state the finding directly
- If data is empty, say clearly what was not found and suggest rephrasing

Language: respond in {language}. If Arabic, use formal business Arabic."""


_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def generate_dax(user_question: str) -> str:
    """Generate a DAX query for the given natural-language question."""
    client = _get_client()
    msg = client.messages.create(
        model=_MODEL,
        max_tokens=512,
        system=_DAX_SYSTEM,
        messages=[{"role": "user", "content": user_question}],
    )
    dax = msg.content[0].text.strip()
    logger.info("dax_generated", extra={"extra": {"model": _MODEL, "chars": len(dax)}})
    return dax


def narrate_result(
    user_question: str,
    dax_query: str,
    raw_data: str,
    language: str,
) -> str:
    """Narrate Power BI query results as a business insight."""
    client = _get_client()
    lang_label = "English" if language == "en" else "Arabic"
    system = _NARRATION_SYSTEM.format(language=lang_label)
    prompt = (
        f"User question: {user_question}\n\n"
        f"DAX query used:\n{dax_query}\n\n"
        f"Data returned:\n{raw_data}"
    )
    msg = client.messages.create(
        model=_MODEL,
        max_tokens=300,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    narrative = msg.content[0].text.strip()
    logger.info(
        "narration_generated",
        extra={"extra": {"model": _MODEL, "language": language, "chars": len(narrative)}},
    )
    return narrative
