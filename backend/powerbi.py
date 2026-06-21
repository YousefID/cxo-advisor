"""Power BI DAX execution layer.

Calls the Power BI executeQueries REST API with a cached Bearer token.
Every query and result summary is logged to logs/queries.log for audit.

Data classification: Internal — query results may contain aggregate
workforce data. Never log individual employee IDs or names.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, UTC
from pathlib import Path

import httpx

from backend.auth import get_access_token
from backend.logging_config import get_logger

logger = get_logger("advisor.powerbi")

_LOG_DIR = Path("logs")
_QUERY_LOG = _LOG_DIR / "queries.log"
_TIMEOUT = 30.0


def _ensure_log_dir() -> None:
    _LOG_DIR.mkdir(exist_ok=True)


def _log_query(dax: str, response_summary: str) -> None:
    _ensure_log_dir()
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "dax_hash": hash(dax) & 0xFFFFFFFF,  # hash only — no raw DAX in prod logs
        "response": response_summary,
    }
    with _QUERY_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def execute_dax(dax_query: str) -> str:
    """Execute a DAX query against the configured Power BI dataset.

    Returns a JSON string of rows, or an error description string.
    """
    workspace_id = os.environ.get("POWERBI_WORKSPACE_ID", "")
    dataset_id = os.environ.get("POWERBI_DATASET_ID", "")

    if not workspace_id or not dataset_id:
        return "Power BI workspace/dataset IDs not configured"

    url = (
        f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}"
        f"/datasets/{dataset_id}/executeQueries"
    )

    token = get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {
        "queries": [{"query": dax_query}],
        "serializerSettings": {"includeNulls": True},
    }

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(url, headers=headers, json=body)
    except httpx.TimeoutException:
        _log_query(dax_query, "TIMEOUT")
        return "Query timed out after 30 seconds"
    except httpx.RequestError as exc:
        _log_query(dax_query, f"REQUEST_ERROR: {exc}")
        return f"Unable to connect to Power BI: {exc}"

    if resp.status_code != 200:
        msg = f"Power BI API error {resp.status_code}: {resp.text}"
        _log_query(dax_query, msg)
        return msg

    data = resp.json()
    try:
        rows = data["results"][0]["tables"][0]["rows"]
    except (KeyError, IndexError):
        _log_query(dax_query, "No data")
        return "No data found for this query"

    if not rows:
        _log_query(dax_query, "Empty rows")
        return "No data found for this query"

    result_str = json.dumps(rows, ensure_ascii=False)
    _log_query(dax_query, f"{len(rows)} rows returned")
    logger.info(
        "dax_executed",
        extra={"extra": {"rows": len(rows), "workspace_id": workspace_id}},
    )
    return result_str
