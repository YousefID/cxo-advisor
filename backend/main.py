"""ZFP Advisor — FastAPI application entry point.

Endpoints:
  GET  /              → serves static/index.html
  GET  /health        → basic health check (Claude + Power BI)
  GET  /debug         → verbose diagnostics JSON
  POST /ask           → AI workforce Q&A
  POST /api/messages  → Microsoft Teams Bot Framework webhook
"""

from __future__ import annotations

import json
import os
import traceback
from datetime import datetime, UTC
from pathlib import Path

from dotenv import load_dotenv

# Always resolve .env relative to this file's parent (project root)
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
    version="1.0.0",
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
    return JSONResponse({"message": "ZFP Advisor API", "version": "1.0.0"})


@app.get("/health", response_model=HealthResponse)
async def health():
    powerbi_status = "error"
    claude_status = "connected"

    try:
        from backend.auth import get_access_token
        get_access_token()
        powerbi_status = "connected"
    except Exception as exc:
        _log_error("health/powerbi", str(exc))

    try:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key or key.startswith("sk-ant-your"):
            claude_status = "error"
    except Exception:
        claude_status = "error"

    return HealthResponse(status="ok", powerbi=powerbi_status, claude=claude_status)


@app.get("/debug")
async def debug():
    """Verbose component health check — tests each subsystem independently."""
    report: dict = {
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "1.0.0",
        "teams_bot": "ready" if _teams_ready else "disabled (MicrosoftAppId/Password not set)",
        "claude": {
            "status": "untested",
            "model": os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5"),
            "response_preview": None,
            "error": None,
        },
        "powerbi_auth": {
            "status": "untested",
            "error": None,
        },
        "powerbi_query": {
            "status": "untested",
            "dax": "EVALUATE ROW(\"Test\", \"ok\", \"RowCount\", COUNTROWS(TS_DTL))",
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
            model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5"),
            max_tokens=16,
            messages=[{"role": "user", "content": "Reply with one word: healthy"}],
        )
        report["claude"]["status"] = "ok"
        report["claude"]["response_preview"] = msg.content[0].text.strip()
    except Exception as exc:
        report["claude"]["status"] = "error"
        report["claude"]["error"] = str(exc)

    # Power BI auth
    token: str | None = None
    try:
        from backend.auth import get_access_token
        token = get_access_token()
        report["powerbi_auth"]["status"] = "ok"
    except Exception as exc:
        report["powerbi_auth"]["status"] = "error"
        report["powerbi_auth"]["error"] = str(exc)

    # Power BI query
    if token is None:
        report["powerbi_query"]["status"] = "skipped"
        report["powerbi_query"]["error"] = "Skipped — fix auth first"
    else:
        try:
            from backend.powerbi import execute_dax
            result = execute_dax(report["powerbi_query"]["dax"])
            if result.startswith("Power BI API error") or result.startswith("Unable"):
                report["powerbi_query"]["status"] = "error"
                report["powerbi_query"]["error"] = result
            else:
                report["powerbi_query"]["status"] = "ok"
                report["powerbi_query"]["rows_returned"] = len(json.loads(result)) if result.startswith("[") else 1
        except Exception as exc:
            report["powerbi_query"]["status"] = "error"
            report["powerbi_query"]["error"] = str(exc)

    statuses = [report["claude"]["status"], report["powerbi_auth"]["status"]]
    report["overall"] = (
        "all systems operational" if all(s == "ok" for s in statuses)
        else f"issues detected — check claude/powerbi_auth fields"
    )
    return JSONResponse(content=report)


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    from backend.advisor import generate_dax, narrate_result
    from backend.powerbi import execute_dax

    dax_query = ""

    try:
        dax_query = generate_dax(req.question)
    except Exception as exc:
        _log_error("ask/generate_dax", str(exc))
        return AskResponse(answer="AI service temporarily unavailable", dax_query="", status="error")

    try:
        raw_data = execute_dax(dax_query)
    except Exception as exc:
        _log_error("ask/execute_dax", str(exc))
        return AskResponse(
            answer=f"Query failed. DAX attempted:\n\n{dax_query}",
            dax_query=dax_query,
            status="error",
        )

    if raw_data.startswith("Power BI API error") or raw_data.startswith("Unable"):
        return AskResponse(
            answer=f"Query failed — {raw_data}\n\nDAX:\n{dax_query}",
            dax_query=dax_query,
            status="error",
        )

    try:
        answer = narrate_result(req.question, dax_query, raw_data, req.language)
    except Exception as exc:
        _log_error("ask/narrate", str(exc))
        return AskResponse(answer="AI service temporarily unavailable", dax_query=dax_query, status="error")

    return AskResponse(answer=answer, dax_query=dax_query, status="success")


@app.post("/api/messages")
async def messages(request: Request) -> Response:
    """Microsoft Teams Bot Framework webhook endpoint."""
    if not _teams_ready or _bot_adapter is None or _bot is None:
        return JSONResponse(
            {"error": "Teams bot not configured (MicrosoftAppId/Password not set)"},
            status_code=503,
        )

    from botbuilder.integration.aiohttp import aiohttp_error_middleware
    from botbuilder.schema import Activity as BFActivity

    body = await request.json()
    activity = BFActivity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")

    invoke_response = await _bot_adapter.process_activity(activity, auth_header, _bot.on_turn)
    if invoke_response:
        return JSONResponse(content=invoke_response.body, status_code=invoke_response.status)
    return Response(status_code=201)
