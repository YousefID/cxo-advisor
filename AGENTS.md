# ZFP Executive Committee Dashboard — AGENTS.md

## Project Overview
An interactive AI-powered executive dashboard for ZFP Group CEO and Executive Committee.
Built using a 4-agent Claude Code pipeline. Adapts the Beacon Coffee COO dashboard pattern
for an A&E firm operating in Saudi Arabia and Egypt.

**Target URL:** https://ceoassistant.uaenorth.cloudapp.azure.com/exec/
**Stack:** FastAPI backend (existing) + React/HTML frontend + Claude API
**Data sources:** PTS Timesheet Excel, Finance Excel, Project Status reports (future)

---

## Architecture

### What This Builds
1. **Action Check Screen** — CEO/Exec reviews open actions each session, marks closed/escalated
2. **Executive Dashboard** — Live KPIs, alerts, project pipeline, AR status, utilization
3. **AI Chat** — Click any tile or action → pre-loaded question → AI answers in 2-3 sentences
4. **Action Register** — Persistent action tracking stored in JSON on server
5. **Multi-exec Views** — CEO, CFO, COO each see relevant tiles

### Data Flow
```
PTS Excel (SharePoint/local) → /kpis endpoint (existing)
Finance Excel (local) → /kpis/finance endpoint (existing)
Action Register (JSON file) → /exec/actions endpoint (new)
Project Status (markdown) → /exec/projects endpoint (new)
All → Claude API → AI responses in dashboard chat
```

---

## Agent Roles

### 🎯 ORCHESTRATOR
**File:** `ORCHESTRATOR_PROMPT.md`
**Tool:** Claude.ai Projects (this file)
**Role:** Reads AGENTS.md, assigns tasks to Builder, validates Reviewer output, triggers Deployer
**Gates:**
- Gate 1: Approve architecture before Builder starts
- Gate 2: Review Builder output before Reviewer runs
- Gate 3: Final approval before Deployer runs

### 🏗️ BUILDER
**Tool:** Claude Code (terminal)
**Working directory:** `~/zfp-exec-dashboard/`
**Builds:**
1. `exec_dashboard.html` — Full interactive dashboard (single file, self-contained)
2. `exec_actions.py` — FastAPI routes for action register CRUD
3. `exec_data.py` — Data aggregation combining workforce + finance KPIs
4. `action_register.json` — Initial action register for ZFP

### 🔍 REVIEWER
**Tool:** Claude Code (new session) or Claude.ai
**Reviews:**
- HTML renders correctly (no broken layouts)
- AI chat calls /ask endpoint correctly
- Action states persist via localStorage
- Arabic/English language toggle works
- All KPI tiles have data-ask attributes
- Mobile responsive

### 🚀 DEPLOYER
**Tool:** Claude Code (terminal) with Azure Run Command
**Deploys to:** Azure VM `askhr-zfp` UAE North
**Steps:**
1. Copy HTML to `/home/azureuser/zfp-advisor/static/exec_dashboard.html`
2. Append exec routes to `/home/azureuser/zfp-advisor/backend/main.py`
3. Deploy action register JSON
4. Restart service
5. Verify endpoint

---

## Build Specification

### Screen 1: Action Check (opens first)
```
┌─────────────────────────────────────────────┐
│ ZFP CEO ADVISOR    [Week 26]    [EN] [AR]   │
│ Good morning, Mr. CEO — 3 actions to review │
├─────────────────────────────────────────────┤
│ ACTION REGISTER — Review before you proceed │
│ [7 open · 4 closed]                         │
├──────────────────┬──────────────────────────┤
│ ACT-001          │ ACT-002                  │
│ Utilization plan │ CFO Finance review       │
│ [Open][Closed]   │ [Open][Closed][Escalate] │
├──────────────────┴──────────────────────────┤
│          [BUILD MY DASHBOARD →]             │
└─────────────────────────────────────────────┘
```

### Screen 2: Executive Dashboard
```
┌──────────────────────────────────────────────────────────┐
│ ZFP CEO ADVISOR  Week 26  ⚠ 2 alerts  [EN][AR]          │
├────────────┬────────────┬────────────┬───────────────────┤
│ 757        │ 54.5%      │ 233        │ SAR 239M          │
│ EMPLOYEES  │ UTILIZATION│ PROJECTS   │ CONTRACT PORTFOLIO │
│ ↑ This wk  │ ↓ Below 65%│ Active     │ SAR 132M invoiced │
├────────────┴────────────┴────────────┴───────────────────┤
│ UTILIZATION BY BU        │ AR STATUS                     │
│ Supervision  [████] 61%  │ Outstanding: SAR 32.3M        │
│ Design       [████] 47%  │ At Risk 60+: SAR 20.5M ⚠     │
│ Corporate    [████] 12%  │ Avg Age: 93 days              │
├──────────────────────────┼───────────────────────────────┤
│ OPEN ACTIONS             │ AI ADVISOR CHAT               │
│ ACT-001 Utilization plan │ ┌─────────────────────────┐  │
│ ACT-002 CFO review   ←── │ │ Click any tile to ask   │  │
│ ACT-003 Project X        │ │ or type below           │  │
│ [escalated] Board deck   │ └─────────────────────────┘  │
├──────────────────────────┴───────────────────────────────┤
│ QUICK QUESTIONS:                                          │
│ [Utilization this week] [AR at risk] [Top projects]      │
└──────────────────────────────────────────────────────────┘
```

### ZFP Action Register (initial)
```json
[
  { "id": "ACT-001", "desc": "Develop utilization improvement plan for Design BU", "owner": "COO", "due": "2026-06-22", "priority": "High", "source": "Dashboard Alert" },
  { "id": "ACT-002", "desc": "CFO to present Finance data validation timeline", "owner": "CFO", "due": "2026-06-22", "priority": "High", "source": "Finance Dashboard" },
  { "id": "ACT-003", "desc": "Review top 5 AR at risk projects with collections team", "owner": "CFO", "due": "2026-06-25", "priority": "High", "source": "Finance Dashboard" },
  { "id": "ACT-004", "desc": "Saudization plan — Design BU at 10% vs target 20%", "owner": "HR Director", "due": "2026-06-30", "priority": "Medium", "source": "Workforce Dashboard" },
  { "id": "ACT-005", "desc": "Project pipeline review — 4-week utilization decline", "owner": "COO", "due": "2026-06-25", "priority": "High", "source": "Trend Alert" }
]
```

---

## AI Chat Context (injected per session)
```javascript
const zfpContext = {
  company: "Zuhair Fayez Partnership (ZFP Group)",
  user: "Mr. CEO",
  market: "Saudi Arabia & Egypt — Architecture & Engineering",
  week: "Week 26, 2026",
  kpis: {
    headcount: 757,
    utilization: 54.5,
    target_util: 65,
    projects: 233,
    total_contract: "SAR 239M",
    total_invoiced: "SAR 132.5M",
    outstanding_ar: "SAR 32.3M",
    ar_at_risk: "SAR 20.5M",
    avg_margin: "44%",
    saudization: "24%"
  },
  alerts: [
    "Billable utilization 54.5% — 10.5 points below 65% target",
    "SAR 20.5M AR overdue 60+ days — immediate collection action needed",
    "Design BU Saudization at 10% — below Nitaqat compliance threshold"
  ],
  market_context: "Vision 2030 mega-projects driving strong pipeline demand. Q3 2026 expected surge in government RFPs."
}
```

---

## File Structure
```
zfp-exec-dashboard/
├── AGENTS.md                    ← This file (Orchestrator reads)
├── ORCHESTRATOR_PROMPT.md       ← Orchestrator instructions
├── BUILD_SPEC.md                ← Detailed spec for Builder
├── REVIEW_CHECKLIST.md          ← Checklist for Reviewer
├── DEPLOY_GUIDE.md              ← Step-by-step for Deployer
├── output/
│   ├── exec_dashboard.html      ← Builder output (main deliverable)
│   ├── exec_routes.py           ← Builder output (FastAPI routes)
│   └── action_register.json     ← Builder output (initial actions)
└── review/
    └── review_report.md         ← Reviewer output
```

---

## Human Gates
1. **Gate 1** — You approve AGENTS.md before Builder starts
2. **Gate 2** — You review Builder output (open HTML in browser)
3. **Gate 3** — You approve deployment to live Azure VM
4. **Gate 4** — You test live URL and provide feedback
5. **Gate 5** — Sign off for sharing with Executive Committee

---

---

## Risk & Opportunities Panel

### Design Principle
Auto-generated from live data — no manual input. CEO sees the risk register the moment
he opens the dashboard, derived from the same PTS and Finance data already connected.

### Risk Matrix (auto-scored from live data)

| Risk ID | Trigger | Severity | Source |
|---------|---------|----------|--------|
| R-001 | Utilization < 65% | HIGH if < 55%, MEDIUM if 55-65% | /kpis |
| R-002 | AR Age > 60 days | HIGH if > SAR 15M at risk, MEDIUM if 5-15M | /kpis/finance |
| R-003 | AR Age > 90 days | CRITICAL — immediate escalation | /kpis/finance |
| R-004 | Utilization declining 3+ consecutive weeks | HIGH | /kpis trend |
| R-005 | Single BU utilization < 40% | HIGH | /kpis by_unit |
| R-006 | Saudization < 20% any BU | MEDIUM (Nitaqat compliance) | /kpis |
| R-007 | Over-budget projects > 2 | MEDIUM | /kpis/finance |
| R-008 | Gross margin < 35% | HIGH | /kpis/finance |

### Opportunity Matrix (auto-scored from live data)

| Opp ID | Trigger | Level | Source |
|--------|---------|-------|--------|
| O-001 | Utilization > 70% | Capacity expansion signal | /kpis |
| O-002 | Margin > 50% on any BU | Scale that BU | /kpis/finance |
| O-003 | AR collection rate > 85% | Strong cash position | /kpis/finance |
| O-004 | Supervision BU > 65% util | Pipeline is strong | /kpis |

### Visual Design
```
┌─────────────────────────────────────────────────────┐
│ RISK & OPPORTUNITIES                    [Live Data] │
├───────────────────────┬─────────────────────────────┤
│ 🔴 CRITICAL (1)       │ 🟡 MEDIUM (2)               │
│ AR overdue 90+ days   │ Design BU Saudization 10%  │
│ SAR 2.1M — J23-01200  │ 2 projects over budget     │
├───────────────────────┼─────────────────────────────┤
│ 🔴 HIGH (2)           │ 🟢 OPPORTUNITIES (1)        │
│ Utilization 54.5%     │ Supervision BU strong      │
│ Design BU at 47%      │ Pipeline expanding Q3      │
└───────────────────────┴─────────────────────────────┘
```

Each risk/opportunity card is **clickable** → pre-fills AI chat with:
`"Explain risk [R-001] and what immediate actions should I take as CEO?"`

### Severity Colors
- 🔴 CRITICAL: `#dc2626` (red) — immediate CEO attention
- 🔴 HIGH: `#ef4444` (red-500) — this week
- 🟡 MEDIUM: `#f59e0b` (amber) — this month
- 🟢 OPPORTUNITY: `#22c55e` (green) — capitalize on this

### Arabic translations
- Risk → مخاطر
- Opportunity → فرص
- Critical → حرج
- High → عالي
- Medium → متوسط

---

## Success Criteria
- [ ] Dashboard loads in < 2 seconds
- [ ] All 5 KPI tiles clickable → pre-loaded AI question
- [ ] Action check screen works (open/closed/escalated)
- [ ] Actions persist across sessions (localStorage)
- [ ] AI chat answers in 2-3 sentences using ZFP context
- [ ] Arabic toggle works on all text
- [ ] Finance section shows DEMO DATA watermark
- [ ] Risk & Opportunities panel auto-generates from live data
- [ ] Risk severity correctly calculated (CRITICAL/HIGH/MEDIUM)
- [ ] Opportunities surface when metrics exceed targets
- [ ] Each risk/opportunity card clickable → AI chat
- [ ] Risk panel updates every time /kpis data refreshes
- [ ] Works on mobile (CEO uses phone)
- [ ] Accessible at https://ceoassistant.uaenorth.cloudapp.azure.com/exec/

---

## Session Handoff Notes
- Existing ZFP CEO Advisor is at `/home/azureuser/zfp-advisor/`
- FastAPI service: `zfp-advisor.service` on port 8001
- Nginx config: `/etc/nginx/sites-available/ceoassistant`
- `/kpis` endpoint returns live workforce data
- `/kpis/finance` endpoint returns finance data
- `/ask` endpoint handles AI queries
- Azure Run Command is the deployment method (heredocs don't work — use printf or base64)
