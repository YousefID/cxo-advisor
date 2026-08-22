"""PostgreSQL (Neon) query execution layer — replaces backend/powerbi.py.

Executes AI-generated SQL against Postgres in place of the old Power BI
DAX path. Every query and result summary is logged to logs/queries.log
for audit, matching the previous logging contract (query text is hashed,
never logged raw, per Internal-tier data classification).

Safety model (see MIGRATION.md "Things that will bite" / non-negotiables):
  1. Only a single SELECT (or WITH ... SELECT) statement is ever allowed.
  2. Statement-level keyword blocklist rejects any write/DDL/multi-statement
     attempt before it reaches the database.
  3. Every query is wrapped and capped with an outer LIMIT, regardless of
     what the model generated.
  4. A Postgres statement_timeout bounds worst-case runtime.
  5. DATABASE_URL should point at a role with SELECT-only grants (the
     app_readonly role) — this module enforces read-only at the session
     level too, but the DB-level grant is the layer that still holds if
     this code has a bug.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, UTC
from pathlib import Path

import psycopg2
import psycopg2.errors
import psycopg2.extras

from backend.logging_config import get_logger

logger = get_logger("advisor.sql_query")

_LOG_DIR = Path("logs")
_QUERY_LOG = _LOG_DIR / "queries.log"

_MAX_ROWS = 200
_STATEMENT_TIMEOUT_MS = 10_000  # 10 seconds

# Blocks writes, DDL, and statement separators. Word-boundary matched so it
# doesn't false-positive on column/table names that merely contain these
# substrings (e.g. "created_at" is fine; "CREATE TABLE" is not).
_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|CREATE|COPY|"
    r"CALL|EXECUTE|VACUUM|MERGE|REFRESH)\b",
    re.IGNORECASE,
)


def _ensure_log_dir() -> None:
    _LOG_DIR.mkdir(exist_ok=True)


def _log_query(sql: str, response_summary: str) -> None:
    _ensure_log_dir()
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "sql_hash": hash(sql) & 0xFFFFFFFF,  # hash only — no raw SQL in prod logs
        "response": response_summary,
    }
    with _QUERY_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _validate_sql(sql: str) -> str | None:
    """Returns an error string if the query is rejected, else None."""
    stripped = sql.strip()

    body = stripped[:-1] if stripped.endswith(";") else stripped
    if ";" in body:
        return "Multiple statements are not permitted"

    upper = body.upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        return "Only SELECT queries are permitted"

    if _FORBIDDEN.search(body):
        return "Query contains a disallowed keyword"

    return None


def execute_sql(sql_query: str) -> str:
    """
    Runs a single read-only SQL query and returns a JSON string of the rows,
    or a human-readable error/status string. Mirrors the return shape of the
    old execute_dax() in backend/powerbi.py so main.py's error-string checks
    can be updated with minimal churn.
    """
    error = _validate_sql(sql_query)
    if error:
        _log_query(sql_query, f"REJECTED: {error}")
        return f"Query rejected: {error}"

    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        return "Database not configured (DATABASE_URL not set)"

    body = sql_query.strip().rstrip(";")
    capped_query = f"SELECT * FROM ({body}) AS _sub LIMIT {_MAX_ROWS}"

    try:
        with psycopg2.connect(dsn, connect_timeout=10) as conn:
            conn.set_session(readonly=True, autocommit=True)
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(f"SET statement_timeout = {_STATEMENT_TIMEOUT_MS}")
                cur.execute(capped_query)
                rows = cur.fetchall()
    except psycopg2.errors.QueryCanceled:
        _log_query(sql_query, "TIMEOUT")
        return "Query timed out after 10 seconds"
    except Exception as exc:
        msg = f"Database error: {exc}"
        _log_query(sql_query, msg)
        return msg

    if not rows:
        _log_query(sql_query, "Empty rows")
        return "No data found for this query"

    result_str = json.dumps(rows, default=str, ensure_ascii=False)
    _log_query(sql_query, f"{len(rows)} rows returned")
    logger.info("sql_executed", extra={"extra": {"rows": len(rows)}})
    return result_str


def check_connection() -> None:
    """Raises on failure — used by /health and /debug. No return value needed;
    callers just care whether this throws."""
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    with psycopg2.connect(dsn, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
