"""Power BI authentication via Service Principal (client credentials flow).

The app authenticates silently using POWERBI_CLIENT_ID + POWERBI_CLIENT_SECRET —
no interactive login, no device code, no token cache files.

Required .env variables:
    POWERBI_TENANT_ID     — Azure AD tenant ID
    POWERBI_CLIENT_ID     — Application (client) ID from Azure AD app registration
    POWERBI_CLIENT_SECRET — Client secret value from Certificates & secrets
"""

from __future__ import annotations

import os
import time

import msal

from backend.logging_config import get_logger

logger = get_logger("advisor.auth")

_SCOPE = ["https://analysis.windows.net/powerbi/api/.default"]

# In-memory cache — avoids a network round-trip on every request
_cache: dict = {}


def _get_authority() -> str:
    tenant_id = os.environ.get("POWERBI_TENANT_ID", "").strip()
    if not tenant_id:
        raise RuntimeError("POWERBI_TENANT_ID is not set in .env")
    return f"https://login.microsoftonline.com/{tenant_id}"


def _get_credentials() -> tuple[str, str]:
    client_id = os.environ.get("POWERBI_CLIENT_ID", "").strip()
    client_secret = os.environ.get("POWERBI_CLIENT_SECRET", "").strip()
    if not client_id:
        raise RuntimeError("POWERBI_CLIENT_ID is not set in .env")
    if not client_secret:
        raise RuntimeError("POWERBI_CLIENT_SECRET is not set in .env")
    return client_id, client_secret


def get_access_token() -> str:
    """Return a valid Power BI Bearer token.

    Tokens are cached in memory and refreshed automatically when they
    are within 60 seconds of expiry.
    """
    now = time.time()
    if _cache.get("token") and _cache.get("expires_at", 0) > now + 60:
        return _cache["token"]

    authority = _get_authority()
    client_id, client_secret = _get_credentials()

    app = msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=authority,
    )

    result = app.acquire_token_for_client(scopes=_SCOPE)

    if "access_token" not in result:
        error = result.get("error_description") or result.get("error") or str(result)
        raise RuntimeError(f"Power BI authentication failed: {error}")

    _cache["token"] = result["access_token"]
    _cache["expires_at"] = now + result.get("expires_in", 3600)
    logger.info("powerbi_token_refreshed", extra={"extra": {"expires_in": result.get("expires_in")}})
    return _cache["token"]


def clear_token_cache() -> None:
    """Clear the in-memory token cache (used in tests)."""
    _cache.clear()
