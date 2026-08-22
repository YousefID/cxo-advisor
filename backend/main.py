"""ZFP Advisor — FastAPI application entry point.

Endpoints:
  GET  /              → serves static/index.html
  GET  /health        → basic health check (Claude + Postgres)
  GET  /debug         → verbose diagnostics JSON
  POST /ask           → AI workforce Q&A
  POST /api/messages  → Microsoft Teams Bot Framework webhook
"""

from __future__ import annotations

import json
import os
from datetime import datetime, UTC
from pathlib import Path

from dotenv import load_dotenv

# Always resolve .env relative to this file's parent (project root).
# On Render there is no .env file — env vars are injected directly into the
# process — so this simply no-ops there, which is fine.
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.logging_config import get_logger
from backend.models import AskRequest, AskResponse, HealthResponse
from backend.exec_routes import exec_router

logger = get_logger("advisor.main")

# ── Bot Framework setup ────────────────────────────────────────────────────────
_bot_adapter = None
_bot = None


def _init_teams() -> bool:
    """Initialise Teams bot components; returns True if credentials are set."""
    global _bot_adapter, _bot
    app_id = os.getenv("MicrosoftAppId", "")
    app_password = os.getenv("MicrosoftAppPassword", "")
    if not app_id or not app_password:
        logger.info("teams_bot_disabled", extra={"extra": {"reason": "MicrosoftAppId/Password not set"}})
        return False

    try:
        from botbuilder.core import BotFrameworkAdapterSettings, BotFrameworkAdapter
        from backend.teams_bot import create_bot

        settings = BotFrameworkAdapterSettings(app_id=app_id, app_password=app_password)
        _bot_adapter = BotFrameworkAdapter(settings)
        _bot = create_bot()
        logger.info("teams_bot_initialized")
        return True
    except ImportError:
        logger.warning("teams_bot_import_failed", extra={"extra": {
            "hint": "Run: pip install botbuilder-core botbuilder-integration-aiohttp"
        }})
        return False


_teams_ready = _init_teams()

# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="ZFP Advisor",
    version="1.1.0",
    description="AI workforce intelligence for ZFP Group leadership",
)

# Serve static files (logo.png, etc.)
_static_dir = Path(__file__).parent.parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")
app.include_router(exec_router)

_error_log = Path("logs") / "errors.log"


def _log_error(context: str, error: str) -> None:
    Path("logs").mkdir(exist_ok=True)
    entry = {"timestamp": datetime.now(UTC).isoformat(), "context": context, "error": error}
    with _error_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    html = Path(__file__).parent.parent / "static" / "index.html"
    if html.exists():
        return FileResponse(str(html))
    return JSONResponse({"message": "ZFP Advisor API", "version": "1.1.0"})


@app.get("/health", response_model=HealthResponse)
async def health():
    db_status = "error"
    claude_status = "connected"

    try:
        from backend.sql_query import check_connection
        check_connection()
        db_status = "connected"
    except Exception as exc:
        _log_error("health/database", str(exc))

    try:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key or key.startswith("sk-ant-your"):
            claude_status = "error"
    except Exception:
        claude_status = "error"

    return HealthResponse(status="ok", database=db_status, claude=claude_status)


@app.get("/debug")
async def debug():
    """Verbose component health check — tests each subsystem independently."""
    report: dict = {
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "1.1.0",
        "teams_bot": "ready" if _teams_ready else "disabled (MicrosoftAppId/Password not set)",
        "claude": {
            "status": "untested",
            "model": os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"),
            "response_preview": None,
            "error": None,
        },
        "database": {
            "status": "untested",
            "error": None,
        },
        "database_query": {
            "status": "untested",
            "sql": "SELECT 'ok' AS test, COUNT(*) AS row_count FROM ts_dtl",
            "rows_returned": None,
            "error": None,
        },
    }

    # Claude
    try:
        import anthropic
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key or key.startswith("sk-ant-your"):
            raise ValueError("ANTHROPIC_API_KEY is missing or still placeholder")
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"),
            max_tokens=16,
            messages=[{"role": "user", "content": "Reply with one word: healthy"}],
        )
        report["claude"]["status"] = "ok"
        report["claude"]["response_preview"] = msg.content[0].text.strip()
    except Exception as exc:
        report["claude"]["status"] = "error"
        report["claude"]["error"] = str(exc)

    # Database connection
    db_ok = False
    try:
        from backend.sql_query import check_connection
        check_connection()
        report["database"]["status"] = "ok"
        db_ok = True
    except Exception as exc:
        report["database"]["status"] = "error"
        report["database"]["error"] = str(exc)

    # Live query
    if not db_ok:
        report["database_query"]["status"] = "skipped"
        report["database_query"]["error"] = "Skipped — fix the database connection first"
    else:
        try:
            from backend.sql_query import execute_sql
            result = execute_sql(report["database_query"]["sql"])
            if result.startswith("Database error") or result.startswith("Query rejected") or result.startswith("Query timed out"):
                report["database_query"]["status"] = "error"
                report["database_query"]["error"] = result
            else:
                report["database_query"]["status"] = "ok"
                try:
                    rows = json.loads(result)
                    report["database_query"]["rows_returned"] = len(rows)
                except (json.JSONDecodeError, TypeError):
                    report["database_query"]["rows_returned"] = None
        except Exception as exc:
            report["database_query"]["status"] = "error"
            report["database_query"]["error"] = str(exc)

    statuses = [report["claude"]["status"], report["database"]["status"]]
    report["overall"] = (
        "all systems operational" if all(s == "ok" for s in statuses)
        else "issues detected — check claude/database fields"
    )
    return JSONResponse(content=report)


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    from backend.advisor import generate_sql, narrate_result
    from backend.sql_query import execute_sql

    sql_query = ""

    try:
        sql_query = generate_sql(req.question)
    except Exception as exc:
        _log_error("ask/generate_sql", str(exc))
        return AskResponse(answer="AI service temporarily unavailable", sql_query="", status="error")

    try:
        raw_data = execute_sql(sql_query)
    except Exception as exc:
        _log_error("ask/execute_sql", str(exc))
        return AskResponse(
            answer=f"Query failed. SQL attempted:\n\n{sql_query}",
            sql_query=sql_query,
            status="error",
        )

    if raw_data.startswith("Database error") or raw_data.startswith("Query rejected") or raw_data.startswith("Query timed out"):
        return AskResponse(
            answer=f"Query failed — {raw_data}\n\nSQL:\n{sql_query}",
            sql_query=sql_query,
            status="error",
        )

    try:
        answer = narrate_result(req.question, sql_query, raw_data, req.language)
    except Exception as exc:
        _log_error("ask/narrate", str(exc))
        return AskResponse(answer="AI service temporarily unavailable", sql_query=sql_query, status="error")

    return AskResponse(answer=answer, sql_query=sql_query, status="success")


@app.post("/api/messages")
async def messages(request: Request) -> Response:
    """Microsoft Teams Bot Framework webhook endpoint."""
    if not _teams_ready or _bot_adapter is None or _bot is None:
        return JSONResponse(
            {"error": "Teams bot not configured (MicrosoftAppId/Password not set)"},
            status_code=503,
        )

    from botbuilder.schema import Activity as BFActivity

    body = await request.json()
    activity = BFActivity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")

    invoke_response = await _bot_adapter.process_activity(activity, auth_header, _bot.on_turn)
    if invoke_response:
        return JSONResponse(content=invoke_response.body, status_code=invoke_response.status)
    return Response(status_code=201)
