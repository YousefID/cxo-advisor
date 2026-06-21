# ZFP Advisor — Claude Code Brief

## What this project is

ZFP Advisor is a bilingual (Arabic/English) AI business advisor for ZFP Group
senior leadership. It answers natural language questions about workforce data
by generating DAX queries, executing them against Power BI, and narrating
results in clear business language.

Accessible via:
1. A standalone web UI at the Azure App Service URL
2. A Microsoft Teams bot (ZFP Advisor bot in Teams)

## Tech stack (do not deviate)

- Backend:    Python 3.11, FastAPI, uvicorn
- AI:         Anthropic Claude API (claude-sonnet-4-5)
- Data:       Power BI REST API — executeQueries endpoint
- Auth:       MSAL service principal (ConfidentialClientApplication)
- Teams:      botbuilder-core + botbuilder-integration-aiohttp
- Frontend:   Single static/index.html — no build step, no framework
- Deployment: Docker -> Azure App Service UAE North
- Tests:      pytest, minimum 80% coverage

## Project structure

    zfp-advisor/
    ├── backend/
    │   ├── __init__.py
    │   ├── main.py           FastAPI app + endpoint registration
    │   ├── advisor.py        generate_dax() + narrate_result()
    │   ├── powerbi.py        execute_dax() — Power BI REST calls
    │   ├── auth.py           get_access_token() — MSAL service principal
    │   ├── teams_bot.py      ZFPAdvisorBot ActivityHandler
    │   ├── logging_config.py structured JSON logging
    │   └── models.py         Pydantic request/response models
    ├── static/
    │   └── index.html        Standalone bilingual web UI
    ├── teams_manifest/
    │   ├── manifest.json
    │   ├── color.png         192x192 Teams icon (from logo.png)
    │   ├── outline.png       32x32 Teams outline icon (from logo.png)
    │   └── ZFPAdvisor.zip    Ready to upload to Teams Admin Center
    ├── tests/
    │   ├── test_advisor.py
    │   ├── test_auth.py
    │   ├── test_powerbi.py
    │   ├── test_teams_bot.py
    │   └── test_main.py
    ├── .env.example
    ├── Dockerfile
    ├── docker-compose.yml
    └── requirements.txt

## Data classification

ALL data in this system is Internal tier.
- Aggregate Power BI results may be sent to Claude API
- Individual employee PII must NEVER be sent to Claude
- API keys must NEVER reach the frontend
- See CLASSIFICATION.md for full policy

## DAX schema (TS_DTL primary table)

Columns: EMP_NO, WEEK_NO(YYYYWW), TS_DATE, RGLR_HRS, OT_HRS,
         PROJECT_NO(blank=overhead), Project_Name, BUSNS_UNIT_NO,
         NATIONALITY_NO("1"=Saudi), TD_ID, DEPT_NO, BRANCH_NO

BILLABLE = PROJECT_NO not blank
OVERHEAD = PROJECT_NO is blank

Related via RELATED(): EMPLOYEES, BUSNS_UNIT, DEPARTMENT, NATIONS,
                        BRANCH, PROJECTS, STATUS, BUSNS_SECTOR

## Local development

    # 1. Create .env from template
    cp .env.example .env

    # 2. Install dependencies
    pip install -r requirements.txt

    # 3. Run the server
    python -m uvicorn backend.main:app --reload --port 8000

    # 4. Run tests
    pytest tests/ -v

    # 5. With Docker
    docker compose up --build

## Environment variables

See .env.example for all required variables.
Key ones:
- ANTHROPIC_API_KEY       from console.anthropic.com
- POWERBI_CLIENT_ID       Azure AD app registration client ID
- POWERBI_CLIENT_SECRET   Azure AD app registration client secret
- POWERBI_TENANT_ID       your Azure AD tenant ID
- MicrosoftAppId          Teams bot registration (optional)
- MicrosoftAppPassword    Teams bot registration (optional)

## Security rules (never violate these)

1. ANTHROPIC_API_KEY stays in backend only — never in frontend JS
2. No individual employee data in any log file
3. MicrosoftAppId/Password stored in Azure Key Vault in production
4. .env file must never be committed to git
5. Token cache is in-memory only — no file-based token persistence
