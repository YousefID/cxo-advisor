# ZFP CEO Advisor — Design Unification Audit
**Date:** 2026-06-21  
**Reviewer Role:** Senior UX/UI Architect (15 years enterprise dashboard experience)  
**Reference:** `/exec/` at https://ceoassistant.uaenorth.cloudapp.azure.com/exec/  
**Source file:** `exec_dashboard.html`

---

## REFERENCE DESIGN SPECIFICATION (exec_dashboard.html)

| Token | Value |
|---|---|
| Background | `--bg: #05070a` |
| Surface | `--surface: #0d1219` |
| Surface 2 | `--surface2: #111a26` |
| Primary Blue | `--primary: #1f6fd6` |
| Primary 2 | `--primary2: #2f86ff` |
| Primary 3 | `--primary3: #0b3f89` |
| Accent | `--accent: #57a7ff` |
| Text | `--text: #f4f7fb` |
| Muted | `--muted: #a7b0bd` |
| Font | `Inter, Segoe UI, Roboto, Arial` |
| Nav active | `color-mix(in srgb, var(--primary) 15%, transparent)` bg + `color: var(--accent)` |
| Theme system | Dropdown picker: Blue Dark / Blue Light / Office / ZFP Gold |
| Light mode | `body.light` class toggle |
| Language | EN/AR with IBM Plex Sans Arabic |

---

## PAGE-BY-PAGE AUDIT

---

### 1. exec_dashboard.html — REFERENCE
**Score: 10 / 10**

The gold standard. All other pages must converge to this.

| Check | Status |
|---|---|
| CSS variable system | PASS — `--primary`, `--accent`, `--surface`, `--surface2`, `--surface3` |
| Font | PASS — Inter, Segoe UI |
| Sidebar | PASS — Logo + nav + user footer, active = accent-tinted blue |
| Topbar | PASS — Brand + center tools + right-tools (theme picker + mode dots + lang) |
| Theme picker | PASS — Dropdown: Blue/Office/ZFP + Dark/Light mode dots |
| Arabic | PASS — RTL, IBM Plex Sans Arabic in font stack |
| Animations | PASS — `@keyframes` shimmer, transitions |
| Nav active accent | PASS — `color-mix(in srgb,var(--primary) 15%,transparent)` + `color:var(--accent)` |
| Branding | PASS — ZFP logo-mark, no personal names |

---

### 2. index.html (AI Advisor)
**Score: 5 / 10**

Theme injection landed but with structural gaps.

| Check | Status | Issue |
|---|---|---|
| Font | PASS | Inter injected |
| Background | PARTIAL | `#0a0c10` vs reference `#05070a` — slightly lighter |
| Gold-to-Blue swap | PASS | `--gold: #1f6fd6` |
| `--gold-dim` | FAIL CRITICAL | Not updated — old gold `rgba(201,168,76,.15)` — nav active halo is AMBER not blue |
| Nav active color | FAIL | `color:var(--gold)` — reference uses `color:var(--accent)` |
| Theme picker | PASS | Dropdown injected |
| Light mode | PASS | `body.light` present |
| Sidebar | FAIL CRITICAL | MISSING — page uses `<header>` + chat layout only — no nav rail |
| Nav items | FAIL | No nav-items to other sections — user is stranded |
| `--surface3` | FAIL | Not defined — only 2 surface levels |
| `--accent` variable | FAIL | `#57a7ff` not defined — referenced by nav active in exec |
| Arabic font | PARTIAL | IBM Plex Sans Arabic NOT in font link |
| Theme JS | PASS | Exec theme system present |

---

### 3. dashboard.html (Workforce Dashboard)
**Score: 5 / 10**

Font and theme picker injected, but colour tokens are broken.

| Check | Status | Issue |
|---|---|---|
| Font | PASS | Inter |
| `--gold` | PASS | `#1f6fd6` |
| `--gold-dim` | FAIL CRITICAL | `rgba(201,168,76,.12)` — STILL OLD GOLD — nav hover/active glows amber |
| `--gold2` orphan | FAIL | `#e0be6a` leftover gold variable polluting CSS |
| Nav active | FAIL | Background is old-gold rgba — appears orange/amber |
| Tab buttons | FAIL | `background:var(--gold);color:#000` — black text on blue background, unreadable |
| Theme picker | PASS | Injected |
| Light mode | PASS | Present |
| `--accent` | FAIL | Not defined |
| `--surface3` | FAIL | Not defined |
| Sidebar active indicator | FAIL | Left-bar uses `--gold-dim` (old gold) — should match exec pattern |
| Arabic font | PASS | IBM Plex Sans Arabic in font link |
| Theme JS | PASS | Present |

---

### 4. finance_dashboard.html
**Score: 5 / 10**

Identical issues to dashboard.html — shared injection.

| Check | Status | Issue |
|---|---|---|
| Font | PASS | Inter |
| `--gold-dim` | FAIL CRITICAL | `rgba(201,168,76,.12)` — old gold — nav hover is amber |
| `--gold2` orphan | FAIL | Same leftover variable |
| Tab buttons | FAIL | Same black-on-blue issue |
| Theme picker | PASS | Present |
| `--accent` | FAIL | Missing |
| `--surface3` | FAIL | Missing |
| Demo data disclaimer | PASS | Appropriate disclosure shown |
| Arabic | PASS | IBM Plex font |
| Theme JS | PASS | Present |

---

### 5. project-analyzer.html
**Score: 3 / 10**

This page was NOT properly updated — retains the OLD gold design system.

| Check | Status | Issue |
|---|---|---|
| Background | FAIL CRITICAL | `#0f1117` vs reference `#05070a` — visibly purple-navy, jarring against other pages |
| `--gold` | FAIL CRITICAL | `#c8a951` — STILL OLD GOLD, NOT blue |
| Surface colors | FAIL | `--surface:#1a1d2e`, `--surface2:#22263a` — wrong, too purple |
| Font | FAIL | System-ui / BlinkMacSystemFont — no Inter loaded |
| `--navy` variable | FAIL | Leftover `--navy:#0d1f3c` — legacy design token |
| Nav active | FAIL | Gold + extra `border:1px solid var(--gold-border)` — not in reference |
| `--gold-border` | FAIL | Extra variable not in reference |
| Theme picker | PARTIAL | Injected but colours wrong because base variables are wrong |
| Light mode | PASS | Body.light present |
| Arabic | FAIL | No IBM Plex Arabic |
| `--accent` | FAIL | Missing |

---

### 6. action_register.html
**Score: 3 / 10**

Uses a completely different theme architecture — incompatible with the reference system.

| Check | Status | Issue |
|---|---|---|
| CSS system | FAIL CRITICAL | Uses `html[data-theme="zfp-dark"]` etc — reference uses `body.theme-*` classes — architecturally incompatible |
| Primary colour | FAIL CRITICAL | `--primary: #c9a84c` (GOLD by default) — exec default is blue |
| Sidebar | FAIL CRITICAL | MISSING — standalone header only — no nav rail — user stranded |
| Theme picker | PARTIAL | Different implementation: inline button row not exec dropdown |
| Theme options | FAIL | Includes Green theme (`#10b981`) — not in reference palette |
| Font | PARTIAL | System fonts — no Inter, no IBM Plex Arabic |
| Light mode | FAIL | Uses `html[data-theme="white-light"]` not `body.light` |
| Arabic font | FAIL | Missing IBM Plex Sans Arabic |
| Animations | FAIL | None — reference has shimmer + card transitions |
| Exec nav link | PASS | `/exec/` link present |

---

### 7. landing.html
**Score: 2 / 10**

Most out-of-date page. Completely untouched by theme injection.

| Check | Status | Issue |
|---|---|---|
| Font | FAIL CRITICAL | Barlow (Google Fonts) — reference uses Inter |
| Colour scheme | FAIL CRITICAL | `--gold: #c9a84c` — still original gold, not updated |
| `--gold-dim` | FAIL | Old gold rgba |
| Theme picker | FAIL | MISSING — no picker at all |
| Theme JS | FAIL | MISSING — no theme system |
| Light mode | FAIL | MISSING |
| Exec nav link | FAIL | No link to `/exec/register/` |
| Arabic font | PASS | IBM Plex Sans Arabic loaded via Google Fonts — only positive |
| Sidebar active | FAIL | Gold indicator, untouched |

---

## CONSOLIDATED ISSUES BY SEVERITY

### CRITICAL — blocks visual coherence

| # | Issue | Pages Affected |
|---|---|---|
| C1 | `--gold-dim` NOT updated — nav hover/active is old amber/orange | dashboard, finance, index |
| C2 | `project-analyzer.html` — wrong background, surfaces, and gold colour | project-analyzer |
| C3 | `landing.html` — Barlow font + old gold — zero unification | landing |
| C4 | `action_register.html` — incompatible theme architecture (`html[data-theme]` vs `body.theme-*`) | action_register |
| C5 | `index.html` + `action_register.html` — NO sidebar — users stranded, no cross-navigation | index, action_register |

### HIGH — visible inconsistency

| # | Issue | Pages Affected |
|---|---|---|
| H1 | `--gold2` orphan variable pollutes CSS with old gold reference | dashboard, finance |
| H2 | Tab buttons (Workforce/Finance toggle): `color:#000` on blue background — illegible | dashboard |
| H3 | `--accent: #57a7ff` variable missing — nav active text colour undefined | all except exec |
| H4 | `--surface3` missing — 3-level depth system incomplete | all except exec |
| H5 | Background `#0a0c10` vs reference `#05070a` | dashboard, finance, index |
| H6 | Nav active CSS: `color:var(--gold)` vs reference `color:var(--accent)` | all except exec |

### LOW — polish

| # | Issue | Pages Affected |
|---|---|---|
| L1 | Card border-radius 12px vs reference 14px | dashboard, finance |
| L2 | `--muted` value: pages use `#6b7280` or `#9ca3af` vs reference `#a7b0bd` | mixed |
| L3 | Green theme in action_register not in reference palette — remove | action_register |
| L4 | Shadow variable not harmonised | mixed |

---

## SCORES SUMMARY

| Page | Score | Status |
|---|---|---|
| exec_dashboard.html | 10 / 10 | REFERENCE — do not modify |
| dashboard.html | 5 / 10 | PARTIAL — critical colour bug |
| finance_dashboard.html | 5 / 10 | PARTIAL — same as dashboard |
| index.html (Advisor) | 5 / 10 | PARTIAL — no sidebar, broken dim |
| project-analyzer.html | 3 / 10 | CRITICAL — wrong base colours, old font |
| action_register.html | 3 / 10 | CRITICAL — incompatible theme architecture |
| landing.html | 2 / 10 | CRITICAL — completely out of date |

**System-wide average: 4.7 / 10**

---

## RECOMMENDED FIX PRIORITY

### Phase 1 — Colour Token Repair (1 session, ~30 min)
1. Fix `--gold-dim` on dashboard, finance, index to `rgba(31,111,214,.15)`
2. Add `--accent:#57a7ff` to all pages
3. Add `--surface3` to all pages
4. Remove `--gold2` orphan
5. Fix nav active: change `color:var(--gold)` to `color:var(--accent)` on all
6. Fix tab button text: `color:#000` to `color:#fff` on Workforce/Finance toggle

### Phase 2 — Page Rebuilds (2 sessions)
7. Rebuild `project-analyzer.html` CSS with correct base variables
8. Rebuild `action_register.html` to use `body.theme-*` system + add sidebar
9. Rebuild `landing.html` — swap Barlow for Inter, apply exec theme, add nav

### Phase 3 — Polish (1 session)
10. Add sidebar to `index.html` (AI Advisor)
11. Harmonise card border-radius to 14px
12. Align `--muted` to `#a7b0bd` everywhere
13. Align background to `#05070a` everywhere
14. Remove Green theme from action_register

---

*Audit complete — awaiting approval to proceed to Builder phase.*
