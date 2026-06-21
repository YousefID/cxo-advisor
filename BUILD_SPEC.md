# BUILD SPEC — ZFP Executive Dashboard

You are the Builder agent. Build these files in `output/`:

## File 1: exec_dashboard.html

### Technical Requirements
- Single HTML file, fully self-contained
- Chart.js from https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js
- No React, no npm, no build step — pure HTML/CSS/JS
- Uses existing `/ask` endpoint for AI chat
- Uses existing `/kpis` endpoint for live data
- Uses existing `/kpis/finance` endpoint for finance data
- localStorage for action state persistence (key: `zfp_exec_actions_v1`)
- sessionStorage for language (`zfp_lang`)

### Color Scheme (match existing ZFP CEO Advisor)
```css
--bg: #0a0c10;
--surface: #111318;
--surface2: #181c24;
--gold: #c9a84c;
--white: #fff;
--text: #e8eaf0;
--muted: #9ca3af;
--border: rgba(255,255,255,.07);
--green: #22c55e;
--red: #ef4444;
--amber: #f59e0b;
```

### Screen 1: Action Check
- Shows on first load
- Displays action cards from action_register.json (hardcoded in JS initially)
- Each card has: ID, description, owner, due date, priority badge
- 3 buttons per card: "Open" / "Closed" / "Escalated"
- Active state saves to localStorage
- Counter shows X open, Y closed, Z escalated
- "BUILD MY DASHBOARD →" button advances to Screen 2

### Screen 2: Executive Dashboard
Layout (CSS Grid):
```
[HEADER: logo, greeting, week, alerts, EN/AR]
[KPI ROW: 4 cards — Employees, Utilization, Projects, Portfolio]
[ROW 2: Utilization by BU (left) | AR Status (right)]
[ROW 3: Open Actions list (left) | AI Chat panel (right)]
[QUICK CHIPS: 5 preset questions]
```

### KPI Cards — each must have data-ask attribute
```javascript
// Clicking a KPI card pre-fills the chat
kpi.dataset.ask = "What is our [metric] and what should I focus on?"
```

### AI Chat Panel
- Uses `/ask` endpoint (POST with `{question, language}`)
- Shows thinking indicator while loading
- Renders answer text
- History stored in sessionStorage (last 10 messages)
- Clear button
- Pre-filled when KPI tile or action item is clicked

### Action List in Dashboard
- Sorted: Escalated → High Open → Medium Open → Closed
- Each item clickable → pre-fills chat with action context
- Status pills: red=escalated, amber=open, green=closed

### Language Toggle
- EN/AR buttons in header
- All UI strings in T={en:{...}, ar:{...}} object
- RTL toggle on html element
- sessionStorage persists across pages

### ZFP Context (inject into every AI call)
```javascript
const ZFP_CONTEXT = `
You are the AI Chief of Staff for the CEO of Zuhair Fayez Partnership (ZFP Group),
a leading Architecture and Engineering firm in Saudi Arabia and Egypt with 789 employees.
Current week: Week 26, 2026.
Live KPIs: [loaded dynamically from /kpis and /kpis/finance]
Market context: Vision 2030 driving strong project pipeline.
A&E industry utilization benchmark: 65-75%.
Voice: Direct, executive, 2-4 sentences max. Never use bullet points.
`;
```

### Translations Required (at minimum)
```javascript
const T = {
  en: {
    appName: 'ZFP CEO ADVISOR',
    screen1Title: 'Action Register',
    screen1Sub: 'Review open actions before proceeding to your dashboard',
    buildBtn: 'Build My Dashboard →',
    open: 'Open', closed: 'Closed', escalated: 'Escalated',
    employees: 'Active Employees', utilization: 'Billable Utilization',
    projects: 'Active Projects', portfolio: 'Contract Portfolio',
    belowTarget: 'Below target', aboveTarget: 'Above target',
    actionRegister: 'Open Actions',
    aiChat: 'AI Advisor',
    thinking: 'Thinking…',
    chatPlaceholder: 'Ask anything about your business…',
    chips: ['Utilization this week', 'AR at risk', 'Top projects by revenue', 'Saudization status', 'Budget vs actual'],
    arStatus: 'AR Status',
    utilByBU: 'Utilization by Business Unit',
    demoNotice: '⚠ Finance figures are demo data pending CFO validation'
  },
  ar: {
    appName: 'مستشار الرئيس التنفيذي ZFP',
    screen1Title: 'سجل الإجراءات',
    screen1Sub: 'راجع الإجراءات المفتوحة قبل المتابعة إلى لوحة التحكم',
    buildBtn: 'ابنِ لوحتي →',
    open: 'مفتوح', closed: 'مغلق', escalated: 'مُصعَّد',
    employees: 'الموظفون النشطون', utilization: 'نسبة الاستخدام القابل للفوترة',
    projects: 'المشاريع النشطة', portfolio: 'محفظة العقود',
    belowTarget: 'دون الهدف', aboveTarget: 'فوق الهدف',
    actionRegister: 'الإجراءات المفتوحة',
    aiChat: 'المستشار الذكي',
    thinking: 'جارٍ التفكير…',
    chatPlaceholder: 'اسأل أي شيء عن أعمالك…',
    chips: ['الاستخدام هذا الأسبوع', 'الذمم المدينة المعرضة للخطر', 'أفضل المشاريع', 'نسبة السعودة', 'الميزانية مقابل الفعلي'],
    arStatus: 'حالة الذمم المدينة',
    utilByBU: 'الاستخدام حسب وحدة الأعمال',
    demoNotice: '⚠ الأرقام المالية بيانات تجريبية بانتظار موافقة المدير المالي'
  }
}
```

---

## File 2: exec_routes.py

```python
# FastAPI routes to append to main.py
# GET /exec/ → serve exec_dashboard.html
# GET /exec/actions → return action_register.json
# POST /exec/actions/{id} → update action status
# GET /exec/context → return combined KPI context for AI
```

---

## File 3: action_register.json

```json
{
  "last_updated": "2026-06-20",
  "actions": [
    {
      "id": "ACT-001",
      "description": "Develop billable utilization improvement plan — Design BU at 47%, 18 points below target",
      "owner": "COO",
      "due_date": "2026-06-22",
      "priority": "High",
      "status": "Open",
      "source": "Dashboard Alert",
      "context": "Design BU utilization has declined 4 consecutive weeks. 79 employees, only 37 on billable projects."
    },
    {
      "id": "ACT-002",
      "description": "CFO to present Finance data validation timeline to CEO",
      "owner": "CFO",
      "due_date": "2026-06-22",
      "priority": "High",
      "status": "Open",
      "source": "Finance Dashboard",
      "context": "Finance dashboard currently showing demo data. Real data connection pending CFO approval of data sharing format."
    },
    {
      "id": "ACT-003",
      "description": "Review top AR at risk projects with collections team — SAR 20.5M overdue 60+ days",
      "owner": "CFO",
      "due_date": "2026-06-25",
      "priority": "High",
      "status": "Open",
      "source": "Finance Dashboard",
      "context": "11 projects with AR age over 60 days. Al Nakheel (SAR 6M, 92 days) and Jeddah Historic District (SAR 3.4M, 99 days) are highest risk."
    },
    {
      "id": "ACT-004",
      "description": "Saudization improvement plan for Design BU — currently 10% vs 20% Nitaqat target",
      "owner": "HR Director",
      "due_date": "2026-06-30",
      "priority": "Medium",
      "status": "Open",
      "source": "Workforce Dashboard",
      "context": "Overall Saudization 24%. Design BU significantly below. Risk of Nitaqat compliance issue in next assessment."
    },
    {
      "id": "ACT-005",
      "description": "Investigate 4-week utilization decline trend — from 78% to 54.5%",
      "owner": "COO",
      "due_date": "2026-06-25",
      "priority": "High",
      "status": "Open",
      "source": "Trend Alert",
      "context": "Week 23: 78%, Week 24: 47%, Week 25: 62%, Week 26: 54.5%. Significant volatility suggests project pipeline gaps."
    }
  ],
  "summary": {
    "total": 5,
    "open": 5,
    "closed": 0,
    "escalated": 0,
    "high_priority_open": 3
  }
}
```

---

## Risk & Opportunities Engine

Add this JavaScript function that runs after KPI data loads:

```javascript
function computeRisks(kpis, finance) {
  const risks = [];
  const opps = [];

  // R-001: Overall utilization
  if (kpis.util < 55) {
    risks.push({ id:'R-001', severity:'HIGH', color:'#ef4444',
      title:'Billable Utilization Critical',
      detail:`${kpis.util}% — ${65 - kpis.util} points below 65% target. Revenue leakage risk.`,
      ask:`Utilization is at ${kpis.util}%, well below the 65% target. What immediate actions should I take as CEO to recover this week?` });
  } else if (kpis.util < 65) {
    risks.push({ id:'R-001', severity:'MEDIUM', color:'#f59e0b',
      title:'Utilization Below Target',
      detail:`${kpis.util}% — monitor closely this week.`,
      ask:`Utilization is at ${kpis.util}%, below our 65% target. What should I watch for?` });
  }

  // R-002/R-003: AR aging
  if (finance.ar_at_risk > 15000000) {
    risks.push({ id:'R-002', severity:'HIGH', color:'#ef4444',
      title:'AR At Risk — Immediate Action',
      detail:`SAR ${fmtM(finance.ar_at_risk)} overdue 60+ days. Cash flow impact imminent.`,
      ask:`We have SAR ${fmtM(finance.ar_at_risk)} in AR overdue 60+ days. What collection actions should I direct the CFO to take?` });
  }

  // R-004: BU-level utilization
  if (kpis.util_by_unit) {
    kpis.util_by_unit.forEach(bu => {
      if (bu.util < 40) {
        risks.push({ id:'R-005', severity:'HIGH', color:'#ef4444',
          title:`${bu.unit} BU Critically Underutilized`,
          detail:`${bu.unit} at ${bu.util}% — bench cost accumulating.`,
          ask:`${bu.unit} business unit utilization is ${bu.util}%. As CEO, what do I do about idle capacity in this unit?` });
      }
    });
  }

  // R-006: Saudization
  if (kpis.saudi_pct < 20) {
    risks.push({ id:'R-006', severity:'MEDIUM', color:'#f59e0b',
      title:'Saudization Below Nitaqat Threshold',
      detail:`${kpis.saudi_pct}% Saudi nationals — below 20% Nitaqat target. Compliance risk.`,
      ask:`Our Saudization rate is ${kpis.saudi_pct}%, below the 20% Nitaqat target. What are the compliance implications and how do I fix this?` });
  }

  // R-007: Over-budget projects
  if (finance.over_budget_count > 2) {
    risks.push({ id:'R-007', severity:'MEDIUM', color:'#f59e0b',
      title:`${finance.over_budget_count} Projects Over Budget`,
      detail:`SAR ${fmtM(finance.over_budget_amount)} total overrun. Review project controls.`,
      ask:`${finance.over_budget_count} projects are over budget by a total of SAR ${fmtM(finance.over_budget_amount)}. What should I do?` });
  }

  // R-008: Margin
  if (finance.avg_margin < 35) {
    risks.push({ id:'R-008', severity:'HIGH', color:'#ef4444',
      title:'Gross Margin Below Threshold',
      detail:`${finance.avg_margin}% average margin — below 35% minimum target.`,
      ask:`Our average gross margin is ${finance.avg_margin}%, below our 35% threshold. Which projects are dragging margins down?` });
  }

  // OPPORTUNITIES
  if (kpis.util > 70) {
    opps.push({ id:'O-001', color:'#22c55e',
      title:'Strong Utilization — Pipeline Signal',
      detail:`${kpis.util}% utilization — capacity at healthy level. Review Q3 pipeline for expansion.`,
      ask:`Utilization is at ${kpis.util}% which is strong. Should we be hiring or chasing more pipeline opportunities now?` });
  }

  if (finance.avg_margin > 50) {
    opps.push({ id:'O-002', color:'#22c55e',
      title:'Margin Outperformance',
      detail:`${finance.avg_margin}% average margin — above 50% target. Identify what's driving this.`,
      ask:`Our gross margin is ${finance.avg_margin}%, above our target. Which projects or BUs are driving this outperformance?` });
  }

  if (finance.total_ar > 0 && (finance.total_invoiced - finance.total_ar) / finance.total_invoiced > 0.85) {
    opps.push({ id:'O-003', color:'#22c55e',
      title:'Strong Cash Collection Rate',
      detail:`Collection rate above 85% — healthy cash position.`,
      ask:`Our cash collection rate is strong. How should I deploy this cash advantage strategically?` });
  }

  return { risks, opps };
}

function fmtM(n) {
  return n >= 1000000 ? (n/1000000).toFixed(1)+'M' : (n/1000).toFixed(0)+'K';
}

function renderRisksPanel(risks, opps) {
  const critical = risks.filter(r => r.severity === 'CRITICAL');
  const high = risks.filter(r => r.severity === 'HIGH');
  const medium = risks.filter(r => r.severity === 'MEDIUM');

  // Render in the risk panel div
  const el = document.getElementById('risk-panel');
  if (!el) return;

  let html = '';

  [
    { items: critical, label: lang==='ar'?'حرج':'CRITICAL', bg:'rgba(220,38,38,.12)', border:'#dc2626' },
    { items: high, label: lang==='ar'?'عالي':'HIGH', bg:'rgba(239,68,68,.08)', border:'#ef4444' },
    { items: medium, label: lang==='ar'?'متوسط':'MEDIUM', bg:'rgba(245,158,11,.08)', border:'#f59e0b' },
    { items: opps, label: lang==='ar'?'فرص':'OPPORTUNITIES', bg:'rgba(34,197,94,.08)', border:'#22c55e' }
  ].forEach(group => {
    if (!group.items.length) return;
    group.items.forEach(item => {
      html += `<div class="risk-card" data-ask="${item.ask}"
        style="background:${group.bg};border-left:3px solid ${group.border};border-radius:10px;
               padding:12px 14px;cursor:pointer;margin-bottom:8px;transition:opacity .2s;"
        onmouseover="this.style.opacity='.8'" onmouseout="this.style.opacity='1'">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
          <span style="font-size:10px;font-weight:700;color:${item.color};letter-spacing:.8px;">${group.label} · ${item.id}</span>
          <span style="font-size:10px;color:var(--muted);">↗ Ask AI</span>
        </div>
        <div style="font-size:13px;font-weight:600;color:var(--white);margin-bottom:3px;">${item.title}</div>
        <div style="font-size:11px;color:var(--muted);line-height:1.4;">${item.detail}</div>
      </div>`;
    });
  });

  if (!html) {
    html = `<div style="text-align:center;padding:20px;color:var(--muted);font-size:13px;">
      ✅ ${lang==='ar'?'لا توجد مخاطر حرجة حالياً':'No critical risks detected this week'}
    </div>`;
  }

  el.innerHTML = html;

  // Bind click handlers
  el.querySelectorAll('.risk-card').forEach(card => {
    card.addEventListener('click', () => {
      askAI(card.dataset.ask);
      // Scroll to chat
      document.getElementById('chat-panel').scrollIntoView({ behavior: 'smooth' });
    });
  });
}
```

### Layout Update — Add Risk Panel to Dashboard
Add as 4th row, full width, between the BU/AR row and Actions/Chat row:
```html
<div class="section-header">
  <span id="risk-title">RISK REGISTER & OPPORTUNITIES</span>
  <span style="font-size:11px;color:var(--muted);" id="risk-sub">Auto-generated from live data</span>
</div>
<div id="risk-panel" style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-bottom:14px;">
  <!-- populated by renderRisksPanel() -->
</div>
```

### Arabic labels for risk panel
Add to T object:
```javascript
en: { ..., riskTitle: 'RISK REGISTER & OPPORTUNITIES', riskSub: 'Auto-generated from live data' }
ar: { ..., riskTitle: 'سجل المخاطر والفرص', riskSub: 'مُولَّد تلقائياً من البيانات المباشرة' }
```

---

## Quality Standards
- All KPI values load dynamically from /kpis and /kpis/finance
- Fallback to hardcoded demo values if endpoints fail
- Loading shimmer while data fetches
- Error states handled gracefully
- No console errors
- Passes HTML validation
