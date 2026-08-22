# Migration — Power BI to MySQL

Moving the query layer from Power BI (DAX over the REST API) to MySQL on Cloud
SQL. MySQL becomes the single source of truth; Power BI leaves the advisor path.

Status: schema designed, not yet provisioned. Billing pending.

## What changes

The advisor works in two stages: Claude turns a question into a query, then
something executes it. Stage one changes language, stage two changes target.

| | Now | After |
|---|---|---|
| Query language | DAX | SQL |
| Executor | backend/powerbi.py | backend/mysql_query.py |
| Auth | MSAL device code | MySQL connection string |
| Prompt | _DAX_SYSTEM in advisor.py | _SQL_SYSTEM |
| Source | Power BI dataset | Cloud SQL, me-central1 |

The narration layer (_NARRATION_SYSTEM) is unaffected — it reads result sets,
not queries.

## Order of work

1. Stand up the database

    gcloud sql instances create zfp-advisor-db --database-version=MYSQL_8_0 --tier=db-g1-small --region=me-central1
    gcloud sql databases create zfp_advisor --instance=zfp-advisor-db
    gcloud sql users create advisor --instance=zfp-advisor-db --password=GENERATED

Then apply schema.sql. Verify with SHOW TABLES — expect 9 tables and v_timesheet.

2. Seed it

Per the guidance in SCHEMA.md. Referential integrity and blank-handling matter
more than volume. Load lookups first, then employees and projects, then ts_dtl.
Foreign keys reject rows loaded out of order, which is the point.

3. Write mysql_query.py

Mirror the interface powerbi.py exposes so the calling code does not change.
Read powerbi.py first and match its signature and return shape.

Non-negotiable: parameterised queries only. Claude generates SQL from user
input; string-concatenated queries are an injection path straight into the
database. Also enforce a read-only DB user, a statement timeout, and a row cap.

4. Rewrite the prompt

_DAX_SYSTEM in advisor.py becomes _SQL_SYSTEM. Same structure — schema
description, business rules, common patterns — expressed as MySQL. The measures
in SCHEMA.md translate directly.

Two things to carry across carefully: week_no is a YYYYWW integer, and the
billable rule depends on project_no being blank or not. Both are easy for a
model to get subtly wrong.

5. Swap the call site

One import and one call in advisor.py. Keep powerbi.py on disk — if the
migration stalls, the old path should still work.

6. Verify against known answers

Run questions whose correct answers you already know from Power BI: total hours
for a period, utilisation for a business unit, Saudization. If SQL and DAX
disagree, assume the SQL is wrong until proven otherwise.

## Configuration

Add to .env and .env.example:

    MYSQL_HOST=
    MYSQL_PORT=3306
    MYSQL_DB=zfp_advisor
    MYSQL_USER=advisor
    MYSQL_PASSWORD=
    MYSQL_SSL_CA=

Add to requirements.txt:

    mysql-connector-python>=9.0.0

From a GCP VM, use the Cloud SQL Auth Proxy or a private IP rather than a public
IP with an allowlist.

## Things that will bite

Blank vs NULL. Power BI treated overhead as a blank string. MySQL distinguishes
empty-string from NULL. Choose one on load and enforce it, or billable totals
split in two and neither is right.

Demo data is not real data. This deployment carries synthetic rows for
demonstration. Any dashboard built on it must show a DEMO DATA marker. Before
real ZFP data is ever loaded, revisit hosting — the current target is a personal
Google Cloud account, which is not appropriate for employee records.

Saudization code. nationality_no = 1 for Saudi is unverified. It is a reported
compliance figure. Confirm against the source system.

SQL injection. Restated because it is the highest-severity item: the model
writes queries from user text. Parameterise, restrict the DB user to SELECT,
cap rows, set a timeout.

## Out of scope

finance_query.py, sharepoint.py and the project analyzer were lost with the
Azure VM — see KNOWN_GAPS.md. They are not part of this migration and need
rebuilding separately.
