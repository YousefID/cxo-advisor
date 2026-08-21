# Known Gaps

Recovered from local artifacts after the Azure VM (askhr-zfp) was deleted.
The following were lost and are NOT in this repo:

- `finance_query.py` — `/kpis` and `/kpis/finance` return 404.
  The exec dashboard calls both.
- `project-analyzer.html` and its port-8002 backend
- `dashboard.html`
- `sharepoint.py`, `excel_query.py`, `recommendations.py`

## Working

`/`  `/health`  `/debug`  `/ask` (Claude + Power BI)
`/exec/`  `/exec/register/`  `/exec/actions`  `POST /exec/actions/{id}`  `/exec/context`

## Notes

- `requirements.txt` uses `>=` pins. pip installs anthropic 1.0.0 against
  code written for 0.28.x. Ran fine locally; pin exact versions before production.
- Theme system (Blue Dark / Blue Light / ZFP Gold / Office) is fully specified
  inside the local `fix_pa_final.py` (gitignored) — reference if the analyzer
  is rebuilt.
- Last deployed state was ~August; this recovery reflects June 8 + June 20-21 work.
  Some July changes are not recoverable.

## Power BI auth

MFA blocks username/password (AADSTS50076). Uses device code flow — run authenticate.py interactively once per machine to seed a token. Claude calls work without it; Power BI queries fail until it's done.

## Power BI auth

MFA blocks username/password (AADSTS50076). Uses device code flow — run authenticate.py interactively once per machine to seed a token. Claude calls work without it; Power BI queries fail until it's done.
