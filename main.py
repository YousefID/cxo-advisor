import json
import logging
import os
from datetime import datetime, UTC
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from advisor.models import AskRequest, AskResponse, HealthResponse
from advisor.claude_advisor import generate_sql, narrate_result
from advisor.sql_query import execute_sql, check_connection

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

_ERROR_LOG = Path("logs") / "errors.log"


def _log_error(context: str, error: str) -> None:
    Path("logs").mkdir(exist_ok=True)
    entry = {"timestamp": datetime.now(UTC).isoformat(), "context": context, "error": error}
    with _ERROR_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


app = FastAPI(title="ZFP Advisor", version="1.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/health", response_model=HealthResponse)
async def health():
    db_status = "error"
    claude_status = "connected"

    try:
        check_connection()
        db_status = "connected"
    except Exception as e:
        _log_error("health/database", str(e))

    try:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key or key == "your_anthropic_api_key_here":
            claude_status = "error"
    except Exception:
        claude_status = "error"

    return HealthResponse(status="ok", database=db_status, claude=claude_status)


@app.get("/debug")
async def debug():
    """
    Run a full component health check and return a verbose JSON report.
    Tests Claude API and Postgres connectivity (with a live query) independently.
    Every error is returned in full — nothing is swallowed.
    """
    import traceback
    report: dict = {
        "timestamp": datetime.now(UTC).isoformat(),
        "claude": {
            "status": "untested",
            "model": "claude-sonnet-4-6",
            "response_preview": None,
            "error": None,
            "traceback": None,
        },
        "database": {
            "status": "untested",
            "dsn_host": None,
            "error": None,
            "traceback": None,
        },
        "database_query": {
            "status": "untested",
            "sql": "SELECT 'ok' AS test, COUNT(*) AS row_count FROM ts_dtl",
            "rows_returned": None,
            "raw_response_preview": None,
            "error": None,
            "traceback": None,
        },
    }

    # ── 1. Claude API ────────────────────────────────────────────────────────
    try:
        import anthropic
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key or key == "your_anthropic_api_key_here":
            raise ValueError(
                "ANTHROPIC_API_KEY is missing or still set to the placeholder value. "
                "Update it in your Render environment variables."
            )
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=32,
            messages=[{"role": "user", "content": "Reply with the single word: healthy"}],
        )
        reply = msg.content[0].text.strip()
        report["claude"]["status"] = "ok"
        report["claude"]["response_preview"] = reply
    except Exception as exc:
        report["claude"]["status"] = "error"
        report["claude"]["error"] = str(exc)
        report["claude"]["traceback"] = traceback.format_exc()

    # ── 2. Database connectivity ─────────────────────────────────────────────
    dsn = os.environ.get("DATABASE_URL", "")
    if dsn:
        try:
            # Cheap, safe-to-log host extraction without exposing credentials.
            report["database"]["dsn_host"] = dsn.split("@")[-1].split("/")[0]
        except Exception:
            pass

    db_ok = False
    try:
        check_connection()
        report["database"]["status"] = "ok"
        db_ok = True
    except Exception as exc:
        report["database"]["status"] = "error"
        report["database"]["error"] = str(exc)
        report["database"]["traceback"] = traceback.format_exc()

    # ── 3. Live query ────────────────────────────────────────────────────────
    if not db_ok:
        report["database_query"]["status"] = "skipped"
        report["database_query"]["error"] = (
            "Skipped because the database connection failed — fix that first."
        )
    else:
        try:
            raw = execute_sql(report["database_query"]["sql"])
            if raw.startswith("Database error") or raw.startswith("Query rejected") or raw.startswith("Query timed out"):
                report["database_query"]["status"] = "error"
                report["database_query"]["error"] = raw
            else:
                report["database_query"]["status"] = "ok"
                try:
                    rows = json.loads(raw)
                    report["database_query"]["rows_returned"] = len(rows)
                    report["database_query"]["raw_response_preview"] = rows[:5]
                except (json.JSONDecodeError, TypeError):
                    report["database_query"]["raw_response_preview"] = raw
        except Exception as exc:
            report["database_query"]["status"] = "error"
            report["database_query"]["error"] = str(exc)
            report["database_query"]["traceback"] = traceback.format_exc()

    # ── Summary ──────────────────────────────────────────────────────────────
    statuses = [
        report["claude"]["status"],
        report["database"]["status"],
        report["database_query"]["status"],
    ]
    if all(s == "ok" for s in statuses):
        report["overall"] = "all systems operational"
    elif all(s in ("error", "skipped") for s in statuses):
        report["overall"] = "all systems failing"
    else:
        failing = []
        if report["claude"]["status"] != "ok":
            failing.append("claude")
        if report["database"]["status"] != "ok":
            failing.append("database")
        if report["database_query"]["status"] not in ("ok", "skipped"):
            failing.append("database_query")
        report["overall"] = f"partial failure — check: {', '.join(failing)}"

    return JSONResponse(content=report)


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    sql_query = ""
    raw_data = ""

    try:
        sql_query = generate_sql(req.question)
    except Exception as e:
        _log_error("ask/generate_sql", str(e))
        return AskResponse(
            answer="AI service temporarily unavailable",
            sql_query="",
            raw_data="",
            status="error",
        )

    try:
        raw_data = execute_sql(sql_query)
    except Exception as e:
        _log_error("ask/execute_sql", str(e))
        return AskResponse(
            answer=f"Query failed — here is what was attempted:\n\n{sql_query}",
            sql_query=sql_query,
            raw_data="",
            status="error",
        )

    if raw_data.startswith("Database error") or raw_data.startswith("Query rejected") or raw_data.startswith("Query timed out"):
        return AskResponse(
            answer=f"Query failed — here is what was attempted:\n\n{sql_query}\n\nError: {raw_data}",
            sql_query=sql_query,
            raw_data=raw_data,
            status="error",
        )

    try:
        answer = narrate_result(req.question, sql_query, raw_data, req.language)
    except Exception as e:
        _log_error("ask/narrate", str(e))
        return AskResponse(
            answer="AI service temporarily unavailable",
            sql_query=sql_query,
            raw_data=raw_data,
            status="error",
        )

    return AskResponse(
        answer=answer,
        sql_query=sql_query,
        raw_data=raw_data,
        status="success",
    )
