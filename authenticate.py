"""
One-time Power BI authentication script.

Run this ONCE from the project root before starting the server:

    python authenticate.py

It will print a URL and a short code. Open the URL in your browser,
enter the code, sign in with your ZFP account, and complete MFA.
The token is then cached to logs/.token_cache.json and the server
will refresh it silently from that point on.
"""

import os
import sys
from pathlib import Path

# Make sure the project root is on the path so advisor.* imports work
sys.path.insert(0, str(Path(__file__).parent))

import msal
from dotenv import load_dotenv
load_dotenv()

_AUTHORITY = "https://login.microsoftonline.com/a7f6706f-2e5e-4273-9614-efeec6968702"
_SCOPE = ["https://analysis.windows.net/powerbi/api/.default"]
# Absolute path so the cache lands in the right place regardless of working directory
_PROJECT_ROOT = Path(__file__).resolve().parent
_CACHE_FILE = _PROJECT_ROOT / "logs" / ".token_cache.json"


def main() -> None:
    client_id = os.environ.get("POWERBI_CLIENT_ID", "").strip()
    if not client_id:
        print("\n✗ POWERBI_CLIENT_ID is not set in your .env file.")
        print("  Register an app in Azure AD and add POWERBI_CLIENT_ID=<id> to .env")
        sys.exit(1)

    Path("logs").mkdir(exist_ok=True)

    # Load any existing cache so we don't re-auth if already valid
    cache = msal.SerializableTokenCache()
    if _CACHE_FILE.exists():
        cache.deserialize(_CACHE_FILE.read_text(encoding="utf-8"))

    app = msal.PublicClientApplication(
        client_id=client_id,
        authority=_AUTHORITY,
        token_cache=cache,
    )

    # Try silent first — maybe the cache is still good
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(scopes=_SCOPE, account=accounts[0])
        if result and "access_token" in result:
            if cache.has_state_changed:
                _CACHE_FILE.write_text(cache.serialize(), encoding="utf-8")
            print(f"\n✓ Already authenticated as: {accounts[0].get('username', '(unknown)')}")
            print("  Token is valid — no sign-in needed. You can start the server.\n")
            return

    # Initiate device code flow
    flow = app.initiate_device_flow(scopes=_SCOPE)
    if "user_code" not in flow:
        print(f"\n✗ Could not start device code flow:")
        print(f"  {flow.get('error_description') or flow}")
        sys.exit(1)

    print()
    print("=" * 60)
    print("  Power BI — Sign in required")
    print("=" * 60)
    print(f"  1. Open this URL in your browser:")
    print(f"     {flow['verification_uri']}")
    print()
    print(f"  2. Enter this code when prompted:")
    print(f"     {flow['user_code']}")
    print()
    print(f"  3. Sign in with your ZFP account (abidris@zfp.com)")
    print(f"     and complete MFA if prompted.")
    print()
    print(f"  Waiting … (expires in {flow.get('expires_in', 900) // 60} min)")
    print("=" * 60)

    # Blocks here until the user finishes or the code expires
    result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        error = result.get("error_description") or result.get("error") or str(result)
        print(f"\n✗ Authentication failed: {error}\n")
        sys.exit(1)

    if cache.has_state_changed:
        _CACHE_FILE.write_text(cache.serialize(), encoding="utf-8")

    account = app.get_accounts()[0] if app.get_accounts() else {}
    print()
    print(f"  ✓ Signed in as: {account.get('username', '(unknown)')}")
    print(f"  ✓ Token cached to: {_CACHE_FILE}")
    print()
    print("  You can now start the server:")
    print("  uvicorn main:app --reload")
    print()


if __name__ == "__main__":
    main()
