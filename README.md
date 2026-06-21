# ZFP Advisor

**AI Workforce Intelligence for ZFP Group Senior Leadership**

Ask ZFP Advisor natural language questions about workforce data, billable utilization, project hours, and team performance. It generates DAX queries, runs them against Power BI, and narrates results in clear business language — in both Arabic and English.

---

## Features

- Natural language to DAX — ask questions, get Power BI data
- Bilingual — Arabic and English in a single interface
- Microsoft Teams bot — ask questions directly in Teams
- Standalone web UI — accessible from any browser
- Collapsible DAX viewer — see every query that was run
- Structured logging — audit trail for every query

## Quick start

```bash
# 1. Clone and enter project
cd zfp-advisor

# 2. Create environment file
cp .env.example .env
# Edit .env — add ANTHROPIC_API_KEY, POWERBI_CLIENT_ID, POWERBI_CLIENT_SECRET, POWERBI_TENANT_ID

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
python -m uvicorn backend.main:app --reload --port 8000

# 5. Open http://localhost:8000
```

## Power BI Setup

ZFP Advisor uses a **service principal** (no user login required):

1. Go to [Azure Portal](https://portal.azure.com) → Azure Active Directory → App registrations
2. Create a new registration (e.g. "ZFP Advisor")
3. Under **Certificates & secrets** → create a client secret → copy it
4. Copy the **Application (client) ID** and your **Tenant ID**
5. In Power BI Admin Portal → **Tenant settings** → enable _"Allow service principals to use Power BI APIs"_
6. In your Power BI workspace → **Manage access** → add the service principal as **Member**

Then set in `.env`:
```
POWERBI_TENANT_ID=your-tenant-id
POWERBI_CLIENT_ID=your-app-registration-id
POWERBI_CLIENT_SECRET=your-client-secret
POWERBI_WORKSPACE_ID=d22cea18-4fd9-4655-b61f-ecfca0db3048
POWERBI_DATASET_ID=a577493b-6eb6-4061-acc3-942db4412edd
```

Verify with: `GET /debug`

## Teams Bot Setup

1. Go to [Azure Bot](https://portal.azure.com/#create/Microsoft.AzureBot)
2. Create a new bot resource, copy the **App ID** and **App Password**
3. Set the messaging endpoint to: `https://your-app.azurewebsites.net/api/messages`
4. Add to `.env`:
   ```
   MicrosoftAppId=your-app-id
   MicrosoftAppPassword=your-app-password
   ```
5. Upload `teams_manifest/ZFPAdvisor.zip` to Teams Admin Center (see below)

## Uploading ZFPAdvisor.zip to Teams

1. Open **Microsoft Teams Admin Center** → [admin.teams.microsoft.com](https://admin.teams.microsoft.com)
2. Go to **Teams apps** → **Manage apps** → **Upload**
3. Upload `teams_manifest/ZFPAdvisor.zip`
4. After upload: go to **Permission policies** → allow the app for leadership users

Note: Before uploading, edit `teams_manifest/manifest.json` and replace:
- `${MicrosoftAppId}` with your actual bot App ID
- `${AZURE_APP_NAME}` with your Azure App Service name (e.g. `zfp-advisor`)

Then re-zip: `cd teams_manifest && zip ZFPAdvisor.zip manifest.json color.png outline.png`

## Running Tests

```bash
pip install pytest pytest-asyncio
pytest tests/ -v --tb=short
```

Expected: 35+ tests, all passing.

## Docker

```bash
# Build and run locally
docker compose up --build

# Or build the image only
docker build -t zfp-advisor .
docker run -p 8000:8000 --env-file .env zfp-advisor
```

## Azure Deployment

The GitHub Actions workflows in `.github/workflows/` deploy automatically on push to `main`.

Required GitHub secrets:
| Secret | Description |
|--------|-------------|
| `ACR_REGISTRY` | Azure Container Registry URL |
| `ACR_USERNAME` | ACR admin username |
| `ACR_PASSWORD` | ACR admin password |
| `AZURE_CREDENTIALS` | Azure service principal JSON |
| `AZURE_STATIC_WEB_APPS_API_TOKEN` | Static Web Apps deployment token |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serves web UI |
| GET | `/health` | Basic health check |
| GET | `/debug` | Verbose component diagnostics |
| POST | `/ask` | AI Q&A: `{"question": "...", "language": "en"}` |
| POST | `/api/messages` | Teams Bot Framework webhook |

## Known Limitations

- Power BI DAX is sensitive to table/column name spelling — if data returns empty, check the DAX in the "View Query" panel
- Teams bot responds in plain text markdown — rich Adaptive Cards are a future enhancement
- Token cache is in-memory — restarts require a new MSAL token fetch (instant, automatic)
- Attendance and leave data requires the dataset to contain those tables

## Data Classification

Internal tier. See [CLASSIFICATION.md](CLASSIFICATION.md) for full policy.

---

Owner: Abdalla Idris, CTO — ZFP Group  
Version: 1.0.0 | Gate 2 — Build  
Deployed: Azure UAE North
