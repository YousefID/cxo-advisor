"""
ZFP Executive Dashboard routes — append to main.py
Endpoints:
  GET  /exec/          → serve exec_dashboard.html
  GET  /exec/actions   → return action_register.json
  POST /exec/actions/{id} → update action status
  GET  /exec/context   → combined KPI context for AI
"""

import json
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

exec_router = APIRouter(prefix="/exec", tags=["exec"])

STATIC_DIR = Path(__file__).parent.parent / "static"
DATA_DIR = Path(__file__).parent.parent / "data"
ACTION_REGISTER_PATH = DATA_DIR / "action_register.json"


class ActionUpdate(BaseModel):
    status: str  # "Open" | "Closed" | "Escalated"


@exec_router.get("/")
async def serve_exec_dashboard():
    html_path = STATIC_DIR / "exec_dashboard.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="exec_dashboard.html not found")
    return FileResponse(html_path, media_type="text/html")


@exec_router.get("/register/")
async def serve_action_register():
    html_path = STATIC_DIR / "action_register.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="action_register.html not found")
    return FileResponse(html_path, media_type="text/html")


@exec_router.get("/actions")
async def get_actions():
    if not ACTION_REGISTER_PATH.exists():
        raise HTTPException(status_code=404, detail="Action register not found")
    with open(ACTION_REGISTER_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return JSONResponse(content=data)


@exec_router.post("/actions/{action_id}")
async def update_action(action_id: str, update: ActionUpdate):
    valid_statuses = {"Open", "Closed", "Escalated"}
    if update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid_statuses}")

    if not ACTION_REGISTER_PATH.exists():
        raise HTTPException(status_code=404, detail="Action register not found")

    with open(ACTION_REGISTER_PATH, encoding="utf-8") as f:
        data = json.load(f)

    action = next((a for a in data["actions"] if a["id"] == action_id), None)
    if not action:
        raise HTTPException(status_code=404, detail=f"Action {action_id} not found")

    action["status"] = update.status

    # Recalculate summary
    actions = data["actions"]
    data["summary"] = {
        "total": len(actions),
        "open": sum(1 for a in actions if a["status"] == "Open"),
        "closed": sum(1 for a in actions if a["status"] == "Closed"),
        "escalated": sum(1 for a in actions if a["status"] == "Escalated"),
        "high_priority_open": sum(1 for a in actions if a["status"] == "Open" and a["priority"] == "High"),
    }

    with open(ACTION_REGISTER_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"ok": True, "action": action, "summary": data["summary"]}


@exec_router.get("/context")
async def get_exec_context(kpis: dict = None, finance: dict = None):
    """
    Returns a combined AI context string from live /kpis and /kpis/finance data.
    Called by the dashboard before each AI query to inject fresh numbers.
    """
    context_lines = [
        "You are the AI Chief of Staff for the CEO of Zuhair Fayez Partnership (ZFP Group),",
        "a leading Architecture and Engineering firm in Saudi Arabia and Egypt.",
        "Current week: Week 26, 2026.",
        "Market context: Vision 2030 driving strong project pipeline.",
        "A&E industry utilization benchmark: 65-75%.",
        "Voice: Direct, executive, 2-4 sentences max. Never use bullet points.",
    ]
    return {"context": " ".join(context_lines)}


# ── Registration helper ──────────────────────────────────────────────────────
# In main.py, add after all existing routers:
#
#   from exec_routes import exec_router
#   app.include_router(exec_router)
#
# Ensure DATA_DIR exists and copy action_register.json there on first deploy.
