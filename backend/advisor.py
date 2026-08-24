"""CXO Advisor AI layer — SQL generation and result narration.

Two public functions:
  generate_sql(question) → PostgreSQL query string
  narrate_result(question, sql, data, language) → business narrative string

Both use the Anthropic Claude API (claude-sonnet-4-6).
Data classification: Internal — aggregate workforce and finance data only,
no individual PII (employee names in the seeded demo data are pseudonyms).
"""

from __future__ import annotations

import os

import anthropic

from backend.logging_config import get_logger

logger = get_logger("advisor.claude")

_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

_SQL_SYSTEM = """You are a PostgreSQL query generator. Generate ONLY a single valid,
read-only PostgreSQL query. Return ONLY the SQL, nothing else — no explanation,
no markdown, no backticks, no trailing semicolon, and never more than one
statement. Only SELECT (or WITH ... SELECT) is permitted — never write DDL or
DML of any kind.

PRIMARY VIEW: v_timesheet — one row per timesheet entry, already joined to
every lookup table. Prefer this over the raw tables unless you specifically
need something it doesn't expose.

v_timesheet columns:
td_id, emp_no, emp_name, week_no (YYYYWW integer, current week = MAX(week_no)),
ts_date (date), rglr_hrs (numeric), ot_hrs (numeric), total_hrs (numeric),
project_no (text, NULL/blank = overhead), project_name,
is_billable (boolean), busns_unit_no, busns_unit_name,
dept_no, dept_dscr, branch_no, branch_name,
nationality_no, country_name, is_saudi (boolean, true = Saudi national),
status, status_dscr, busns_sector, sector_dscr

UNDERLYING TABLES (join manually only if v_timesheet doesn't cover the need):
ts_dtl (fact), employees, projects, busns_unit, department, branch,
nations, status, busns_sector — see SCHEMA.md for the full column list and
foreign keys if you need to go beyond the view.

FINANCE TABLES (separate from workforce data — no FK to projects; join on
project_no only where it happens to match, since demo project codes only
partially overlap):
- project_finance: project_no, project_name, sector, business_unit,
  contract_value_sar, start_date, end_date, invoiced_to_date_sar,
  collected_to_date_sar, outstanding_ar_sar, ar_age_days, direct_cost_sar,
  gross_profit_sar, margin_pct, project_status, notes
- monthly_revenue: month (text 'YYYY-MM'), revenue_invoiced_sar,
  direct_costs_sar, gross_profit_sar, margin_pct, cash_collected_sar,
  new_contracts_sar, headcount_cost_sar
- budget_vs_actual: project_no, project_name, budgeted_cost_sar,
  actual_cost_sar, variance_sar, variance_pct, status

Use the finance tables for questions about AR (accounts receivable), revenue,
margin, budget vs actual, cash collection, or contract value. Use
v_timesheet/workforce tables for questions about hours, utilization,
headcount, or Saudization. A question can span both — join on project_no
where present, but expect it not to match for every row.

BILLABLE LOGIC: is_billable = true (equivalently: project_no IS NOT NULL AND project_no <> '')
OVERHEAD LOGIC: is_billable = false

WEEK NUMBER FORMAT: YYYYWW integer (e.g. 202623 = week 23 of 2026).

IMPORTANT — this is a fixed historical dataset, not a live feed. It does not
extend to today's real-world date. Never use CURRENT_DATE or TODAY() to mean
"the current/latest period" — the data ends before today and that filter
will silently return zero rows. Instead, treat "current," "this month," "this
week," "latest," or "recent" as the most recent period actually present in
the data:
- Current week = MAX(week_no) in v_timesheet (or ts_dtl)
- Current month = the month of MAX(ts_date) in v_timesheet — e.g.
  date_trunc('month', ts_date) = (SELECT date_trunc('month', MAX(ts_date)) FROM v_timesheet)
- "Last month" = one calendar month before that latest month, computed the
  same relative way — never relative to CURRENT_DATE.

COMMON PATTERNS:
- Total hours = SUM(total_hrs)
- Billable hours = SUM(rglr_hrs) FILTER (WHERE is_billable)
- Utilization % = billable_hours / NULLIF(total_hours, 0) * 100
- Current month filter = date_trunc('month', ts_date) = (SELECT date_trunc('month', MAX(ts_date)) FROM v_timesheet)
- Saudi headcount = COUNT(DISTINCT emp_no) FILTER (WHERE is_saudi)
- Saudization % = COUNT(DISTINCT emp_no) FILTER (WHERE is_saudi)
    / NULLIF(COUNT(DISTINCT emp_no), 0) * 100

Always alias aggregate/computed columns with a readable name (e.g. AS utilization_pct).
Always include a readable label column (name, not just an ID) alongside numeric results.
Group with GROUP BY as needed; there is no SUMMARIZECOLUMNS equivalent to reach for.
Limit results to 10 rows with LIMIT 10 unless the user explicitly asks for all rows."""

_NARRATION_SYSTEM = """You are CXO Advisor, an AI business advisor for senior leadership.

Your job: interpret workforce and finance data and deliver a clear, confident business answer.

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


def generate_sql(user_question: str) -> str:
    """Generate a read-only PostgreSQL query for the given natural-language question.

    Replaces generate_dax(). Same signature shape, so callers (main.py,
    teams_bot.py) only need the import and function name updated.
    """
    client = _get_client()
    msg = client.messages.create(
        model=_MODEL,
        max_tokens=512,
        system=_SQL_SYSTEM,
        messages=[{"role": "user", "content": user_question}],
    )
    sql = msg.content[0].text.strip()
    logger.info("sql_generated", extra={"extra": {"model": _MODEL, "chars": len(sql)}})
    return sql


def narrate_result(
    user_question: str,
    sql_query: str,
    raw_data: str,
    language: str,
) -> str:
    """Narrate workforce query results as a business insight."""
    client = _get_client()
    lang_label = "English" if language == "en" else "Arabic"
    system = _NARRATION_SYSTEM.format(language=lang_label)
    prompt = (
        f"User question: {user_question}\n\n"
        f"SQL query used:\n{sql_query}\n\n"
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