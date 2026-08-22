# ZFP Advisor — Data Schema

Structure of the workforce dataset, translated from the Power BI semantic model
that the DAX prompt in `backend/advisor.py` was written against.

**This document contains no data.** Table and column definitions only.

Companion file: `schema.sql` — runnable MySQL DDL.

## Model shape

One fact table, eight lookups. Star schema.

    department --+
    branch ------+---> ts_dtl <--- employees
    nations -----+     (fact)
                       |     |
             busns_unit+     +---> projects ---> status
                                            ---> busns_sector

## ts_dtl — timesheet detail (fact)

One row per employee per timesheet entry.

| Column | Type | Notes |
|---|---|---|
| td_id | BIGINT PK | Surrogate key, auto-increment |
| emp_no | VARCHAR(20) | -> employees |
| week_no | INT | YYYYWW, e.g. 202623 = week 23 of 2026. Current week = MAX(week_no) |
| ts_date | DATE | |
| rglr_hrs | DECIMAL(8,2) | Regular hours |
| ot_hrs | DECIMAL(8,2) | Overtime hours |
| project_no | VARCHAR(30) | NULL/blank = overhead. -> projects |
| busns_unit_no | VARCHAR(20) | -> busns_unit |
| nationality_no | VARCHAR(10) | -> nations. 1 = Saudi |
| dept_no | VARCHAR(20) | -> department |
| branch_no | VARCHAR(20) | -> branch |

nationality_no, dept_no, branch_no and busns_unit_no are denormalised onto the
fact table — they also live on employees. This mirrors the Power BI model. Keep
them consistent on load, or queries disagree depending which path they take.

## Lookups

| Table | Key | Label column |
|---|---|---|
| employees | emp_no | emp_name |
| projects | project_no | project_name |
| busns_unit | busns_unit_no | clean_name |
| department | dept_no | dept_dscr |
| branch | branch_no | branch_name |
| nations | nationality_no | country_name |
| status | status | status_dscr |
| busns_sector | busns_sector | sector_dscr |

Power BI named the business-unit label "Clean Name" (with a space). Renamed to
clean_name — unquoted identifiers are less error-prone in generated SQL.

## Business rules

These define the numbers. Wrong here means every dashboard is wrong.

Billable vs overhead:

    -- billable
    WHERE project_no IS NOT NULL AND project_no <> ""
    -- overhead
    WHERE project_no IS NULL OR project_no = ""

Core measures:

    -- total hours
    SUM(rglr_hrs + ot_hrs)

    -- billable hours
    SUM(CASE WHEN project_no IS NOT NULL AND project_no <> ""
             THEN rglr_hrs ELSE 0 END)

    -- utilisation %
    billable_hours / NULLIF(total_hours, 0) * 100

    -- saudization %
    COUNT(DISTINCT CASE WHEN nationality_no = "1" THEN emp_no END)
      / NULLIF(COUNT(DISTINCT emp_no), 0) * 100

VERIFY the nationality code before trusting any Saudization figure. The mapping
came from the DAX prompt, not the source system. It is a reported compliance
number — a wrong code produces a wrong answer that looks entirely plausible.

## Seeding

The database ships empty. Generated data must satisfy these, or reports break in
ways that are hard to trace:

Referential integrity
- Every ts_dtl.emp_no exists in employees
- Every non-blank ts_dtl.project_no exists in projects
- All lookup FKs resolve

Blank handling — pick NULL or empty-string for overhead and apply it everywhere.
A mix silently splits billable totals.

Realistic distributions — uniform random data hides bugs a realistic spread
exposes:
- 70-80% of rows billable
- Weekly hours per employee clustering 40-45, occasional overtime
- week_no continuous across the period, no gaps
- ts_date consistent with its week_no
- Nationality mix roughly matching the real workforce, so Saudization lands in a
  believable range

Scale — ZFP is ~789 employees. A year of weekly entries is roughly 40,000 fact
rows. Enough to surface performance problems, small enough to reload fast.

Label the data. Give employees obviously synthetic names and show a DEMO DATA
marker on the dashboard. Plausible-looking fake numbers get mistaken for real
ones.

## Deployment

Cloud SQL for MySQL 8.0, me-central1 (Doha). Demo data only.

Residency check outstanding: SLFE was placed in me-central2 (Dammam) for Saudi
data residency under NFR-03. ZFP employee data — names, nationality codes,
timesheets — is arguably more sensitive than project backlog figures. Confirm
whether ZFP carries a residency requirement before this ever holds real data.

Character set is utf8mb4 throughout — Arabic appears in employee and project
names.
