# REVIEW CHECKLIST — ZFP Executive Dashboard

You are the Reviewer agent. Check exec_dashboard.html against this list.
Write your findings to review/review_report.md with PASS/FAIL/WARN for each item.

## Screen 1: Action Check
- [ ] Renders without console errors
- [ ] All 5 actions display with correct data
- [ ] Open/Closed/Escalated buttons work and save state
- [ ] Counter updates correctly
- [ ] "Build My Dashboard" button navigates to Screen 2
- [ ] Arabic translation works for all action screen text

## Screen 2: KPI Row
- [ ] 4 KPI cards render correctly
- [ ] Values load from /kpis endpoint
- [ ] Finance values load from /kpis/finance endpoint
- [ ] Utilization shows red arrow when below 65%
- [ ] Utilization shows green arrow when above 65%
- [ ] Clicking each KPI card opens AI chat with pre-loaded question
- [ ] Loading shimmer shows while data fetches
- [ ] Fallback values show if endpoint fails

## Screen 2: Charts/Data
- [ ] Utilization by BU section renders
- [ ] AR Status section renders with correct values
- [ ] Demo data notice appears for finance section

## Action List
- [ ] Open actions display correctly
- [ ] Escalated actions show in red
- [ ] Closed actions show struck-through
- [ ] Clicking action item pre-fills chat

## AI Chat Panel
- [ ] Chat input field works
- [ ] Send button works
- [ ] Thinking indicator appears
- [ ] Response renders as text
- [ ] Chip buttons work
- [ ] Clear button clears history
- [ ] ZFP context is included in every API call

## Language Toggle
- [ ] EN button sets English
- [ ] AR button sets Arabic
- [ ] RTL layout applies correctly in Arabic
- [ ] All strings translate (no hardcoded English in Arabic mode)
- [ ] sessionStorage persists language
- [ ] Greeting changes language

## Risk & Opportunities Panel
- [ ] Panel renders after KPI data loads
- [ ] CRITICAL risks appear in red with correct threshold (AR > 90 days)
- [ ] HIGH risks appear for utilization < 55% and AR > SAR 15M
- [ ] MEDIUM risks appear for Saudization < 20% and over-budget > 2
- [ ] Opportunities appear when metrics exceed targets
- [ ] Each card is clickable → pre-fills AI chat
- [ ] "No critical risks" message shows when all metrics healthy
- [ ] Arabic labels translate correctly
- [ ] Panel updates if /kpis data changes

## Performance
- [ ] Page loads in under 2 seconds (no blocking resources)
- [ ] No external dependencies except Chart.js from cdnjs
- [ ] Works offline except for API calls

## Mobile
- [ ] Layout works on 375px width
- [ ] Buttons are tappable (min 44px)
- [ ] Text is readable (min 13px)

## Security
- [ ] No API keys hardcoded
- [ ] No console.log of sensitive data

## Write report to review/review_report.md
Format:
```
# Review Report — ZFP Executive Dashboard
Date: [today]
Reviewer: Claude Code

## Summary
PASSED: X / FAILED: Y / WARNINGS: Z

## Critical Issues (must fix before deploy)
...

## Minor Issues (fix if time permits)
...

## Recommendation
[APPROVE / APPROVE WITH FIXES / REJECT]
```
