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
from advisor.claude_advisor import generate_dax, narrate_result
from advisor.powerbi import execute_dax

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

_ERROR_LOG = Path("logs") / "errors.log"


def _log_error(context: str, error: str) -> None:
    Path("logs").mkdir(exist_ok=True)
    entry = {"timestamp": datetime.now(UTC).isoformat(), "context": context, "error": error}
    with _ERROR_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


app = FastAPI(title="ZFP Advisor", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/health", response_model=HealthResponse)
async def health():
    powerbi_status = "error"
    claude_status = "connected"

    try:
        from advisor.auth import get_access_token
        get_access_token()
        powerbi_status = "connected"
    except Exception as e:
        _log_error("health/powerbi", str(e))

    try:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key or key == "your_anthropic_api_key_here":
            claude_status = "error"
    except Exception:
        claude_status = "error"

    return HealthResponse(status="ok", powerbi=powerbi_status, claude=claude_status)


@app.get("/debug")
async def debug():
    """
    Run a full component health check and return a verbose JSON report.
    Tests Claude API, Power BI authentication, and a live DAX query independently.
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
        "powerbi_auth": {
            "status": "untested",
            "account": os.environ.get("POWERBI_EMAIL", "(POWERBI_EMAIL not set)"),
            "error": None,
            "traceback": None,
        },
        "powerbi_query": {
            "status": "untested",
            "dax": "EVALUATE ROW(\"Test\", \"ok\", \"RowCount\", COUNTROWS(TS_DTL))",
            "http_status": None,
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
                "Update it in your .env file."
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

    # ── 2. Power BI authentication ───────────────────────────────────────────
    token: str | None = None
    try:
        from advisor.auth import get_access_token
        token = get_access_token()
        report["powerbi_auth"]["status"] = "ok"
    except Exception as exc:
        report["powerbi_auth"]["status"] = "error"
        report["powerbi_auth"]["error"] = str(exc)
        report["powerbi_auth"]["traceback"] = traceback.format_exc()

    # ── 3. Power BI DAX query ────────────────────────────────────────────────
    if token is None:
        report["powerbi_query"]["status"] = "skipped"
        report["powerbi_query"]["error"] = (
            "Skipped because Power BI authentication failed — fix auth first."
        )
    else:
        import httpx
        workspace_id = os.environ.get("POWERBI_WORKSPACE_ID", "")
        dataset_id = os.environ.get("POWERBI_DATASET_ID", "")
        dax = report["powerbi_query"]["dax"]

        if not workspace_id or not dataset_id:
            report["powerbi_query"]["status"] = "error"
            report["powerbi_query"]["error"] = (
                "POWERBI_WORKSPACE_ID or POWERBI_DATASET_ID not set in .env"
            )
        else:
            url = (
                f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}"
                f"/datasets/{dataset_id}/executeQueries"
            )
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            body = {
                "queries": [{"query": dax}],
                "serializerSettings": {"includeNulls": True},
            }
            try:
                with httpx.Client(timeout=30) as http:
                    resp = http.post(url, headers=headers, json=body)

                report["powerbi_query"]["http_status"] = resp.status_code

                if resp.status_code == 200:
                    data = resp.json()
                    try:
                        rows = data["results"][0]["tables"][0]["rows"]
                        report["powerbi_query"]["status"] = "ok"
                        report["powerbi_query"]["rows_returned"] = len(rows)
                        report["powerbi_query"]["raw_response_preview"] = rows[:5]
                    except (KeyError, IndexError) as exc:
                        report["powerbi_query"]["status"] = "error"
                        report["powerbi_query"]["error"] = (
                            f"Unexpected response shape — could not extract rows: {exc}"
                        )
                        report["powerbi_query"]["raw_response_preview"] = data
                else:
                    report["powerbi_query"]["status"] = "error"
                    # Return the full body so the Power BI error message is visible
                    try:
                        body_parsed = resp.json()
                    except Exception:
                        body_parsed = resp.text
                    report["powerbi_query"]["error"] = (
                        f"HTTP {resp.status_code}: {body_parsed}"
                    )
                    report["powerbi_query"]["raw_response_preview"] = body_parsed

            except httpx.TimeoutException:
                report["powerbi_query"]["status"] = "error"
                report["powerbi_query"]["error"] = (
                    "Request timed out after 30 seconds. "
                    "Check that the workspace/dataset IDs are correct and the dataset is online."
                )
                report["powerbi_query"]["traceback"] = traceback.format_exc()
            except Exception as exc:
                report["powerbi_query"]["status"] = "error"
                report["powerbi_query"]["error"] = str(exc)
                report["powerbi_query"]["traceback"] = traceback.format_exc()

    # ── Summary ──────────────────────────────────────────────────────────────
    statuses = [
        report["claude"]["status"],
        report["powerbi_auth"]["status"],
        report["powerbi_query"]["status"],
    ]
    if all(s == "ok" for s in statuses):
        report["overall"] = "all systems operational"
    elif all(s in ("error", "skipped") for s in statuses):
        report["overall"] = "all systems failing"
    else:
        failing = []
        if report["claude"]["status"] != "ok":
            failing.append("claude")
        if report["powerbi_auth"]["status"] != "ok":
            failing.append("powerbi_auth")
        if report["powerbi_query"]["status"] not in ("ok", "skipped"):
            failing.append("powerbi_query")
        report["overall"] = f"partial failure — check: {', '.join(failing)}"

    return JSONResponse(content=report)


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    dax_query = ""
    raw_data = ""

    try:
        dax_query = generate_dax(req.question)
    except Exception as e:
        _log_error("ask/generate_dax", str(e))
        return AskResponse(
            answer="AI service temporarily unavailable",
            dax_query="",
            raw_data="",
            status="error",
        )

    try:
        raw_data = execute_dax(dax_query)
    except Exception as e:
        _log_error("ask/execute_dax", str(e))
        return AskResponse(
            answer=f"Query failed — here is what was attempted:\n\n{dax_query}",
            dax_query=dax_query,
            raw_data="",
            status="error",
        )

    if raw_data.startswith("Power BI API error") or raw_data.startswith("Unable to connect"):
        return AskResponse(
            answer=f"Query failed — here is what was attempted:\n\n{dax_query}\n\nError: {raw_data}",
            dax_query=dax_query,
            raw_data=raw_data,
            status="error",
        )

    try:
        answer = narrate_result(req.question, dax_query, raw_data, req.language)
    except Exception as e:
        _log_error("ask/narrate", str(e))
        return AskResponse(
            answer="AI service temporarily unavailable",
            dax_query=dax_query,
            raw_data=raw_data,
            status="error",
        )

    return AskResponse(
        answer=answer,
        dax_query=dax_query,
        raw_data=raw_data,
        status="success",
    )
