"""
Power BI authentication via Service Principal (client credentials flow).

The app authenticates silently using client_id + client_secret — no
interactive login, no token cache files, no device code flow.

Required .env variables:
    POWERBI_CLIENT_ID     — Application (client) ID from Azure AD app registration
    POWERBI_CLIENT_SECRET — Client secret value from Certificates & secrets
"""

import os
import time
import msal

_TENANT_ID  = "a7f6706f-2e5e-4273-9614-efeec6968702"
_AUTHORITY  = f"https://login.microsoftonline.com/{_TENANT_ID}"
_SCOPE      = ["https://analysis.windows.net/powerbi/api/.default"]

# In-memory cache — avoids a network round-trip on every request
_cache: dict = {}


def _get_credentials() -> tuple[str, str]:
    client_id = os.environ.get("POWERBI_CLIENT_ID", "").strip()
    client_secret = os.environ.get("POWERBI_CLIENT_SECRET", "").strip()
    if not client_id:
        raise RuntimeError("POWERBI_CLIENT_ID is not set in .env")
    if not client_secret:
        raise RuntimeError("POWERBI_CLIENT_SECRET is not set in .env")
    return client_id, client_secret


def get_access_token() -> str:
    """
    Return a valid Power BI Bearer token using client credentials flow.
    Tokens are cached in memory and refreshed automatically when they
    are within 60 seconds of expiry.
    """
    now = time.time()
    if _cache.get("token") and _cache.get("expires_at", 0) > now + 60:
        return _cache["token"]

    client_id, client_secret = _get_credentials()

    app = msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=_AUTHORITY,
    )

    result = app.acquire_token_for_client(scopes=_SCOPE)

    if "access_token" not in result:
        error = result.get("error_description") or result.get("error") or str(result)
        raise RuntimeError(f"Power BI authentication failed: {error}")

    _cache["token"] = result["access_token"]
    _cache["expires_at"] = now + result.get("expires_in", 3600)
    return _cache["token"]


def clear_token_cache() -> None:
    _cache.clear()
