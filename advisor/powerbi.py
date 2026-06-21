import os
import json
import logging
from datetime import datetime, UTC
from pathlib import Path

import httpx

from advisor.auth import get_access_token

logger = logging.getLogger(__name__)

_LOG_DIR = Path("logs")
_QUERY_LOG = _LOG_DIR / "queries.log"


def _ensure_log_dir() -> None:
    _LOG_DIR.mkdir(exist_ok=True)


def _log_query(dax: str, response_summary: str) -> None:
    _ensure_log_dir()
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "dax": dax,
        "response": response_summary,
    }
    with _QUERY_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def execute_dax(dax_query: str) -> str:
    workspace_id = os.environ["POWERBI_WORKSPACE_ID"]
    dataset_id = os.environ["POWERBI_DATASET_ID"]
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
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, headers=headers, json=body)
    except httpx.TimeoutException:
        _log_query(dax_query, "TIMEOUT")
        return "Query timed out after 30 seconds"

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
    return result_str
