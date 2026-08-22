-- ZFP Advisor — PostgreSQL schema (Neon)
-- Converted from schema.sql (MySQL 8.0) — see SCHEMA.md for business rules.
-- STRUCTURE ONLY. No rows. Run against your Neon database with:
--   psql "$DATABASE_URL" -f schema.postgres.sql

-- No CREATE DATABASE — Neon already provisions one database per project.
-- No ENGINE=InnoDB / CHARSET clauses — not applicable in Postgres; Neon
-- databases are UTF8 by default, which covers utf8mb4's use case here.

CREATE TABLE nations (
  nationality_no VARCHAR(10) NOT NULL,
  country_name   VARCHAR(120) NOT NULL,
  PRIMARY KEY (nationality_no)
);

CREATE TABLE branch (
  branch_no   VARCHAR(20) NOT NULL,
  branch_name VARCHAR(120) NOT NULL,
  PRIMARY KEY (branch_no)
);

CREATE TABLE department (
  dept_no   VARCHAR(20) NOT NULL,
  dept_dscr VARCHAR(160) NOT NULL,
  PRIMARY KEY (dept_no)
);

CREATE TABLE busns_unit (
  busns_unit_no VARCHAR(20) NOT NULL,
  clean_name    VARCHAR(160) NOT NULL,
  PRIMARY KEY (busns_unit_no)
);

CREATE TABLE status (
  status      VARCHAR(20) NOT NULL,
  status_dscr VARCHAR(120) NOT NULL,
  PRIMARY KEY (status)
);

CREATE TABLE busns_sector (
  busns_sector VARCHAR(20) NOT NULL,
  sector_dscr  VARCHAR(160) NOT NULL,
  PRIMARY KEY (busns_sector)
);

CREATE TABLE employees (
  emp_no         VARCHAR(20) NOT NULL,
  emp_name       VARCHAR(200),
  dept_no        VARCHAR(20),
  branch_no      VARCHAR(20),
  busns_unit_no  VARCHAR(20),
  nationality_no VARCHAR(10),
  PRIMARY KEY (emp_no),
  CONSTRAINT fk_emp_dept   FOREIGN KEY (dept_no) REFERENCES department (dept_no),
  CONSTRAINT fk_emp_branch FOREIGN KEY (branch_no) REFERENCES branch (branch_no),
  CONSTRAINT fk_emp_bu     FOREIGN KEY (busns_unit_no) REFERENCES busns_unit (busns_unit_no),
  CONSTRAINT fk_emp_nat    FOREIGN KEY (nationality_no) REFERENCES nations (nationality_no)
);
CREATE INDEX idx_emp_dept   ON employees (dept_no);
CREATE INDEX idx_emp_branch ON employees (branch_no);
CREATE INDEX idx_emp_bu     ON employees (busns_unit_no);
CREATE INDEX idx_emp_nat    ON employees (nationality_no);

CREATE TABLE projects (
  project_no   VARCHAR(30) NOT NULL,
  project_name VARCHAR(255),
  status       VARCHAR(20),
  busns_sector VARCHAR(20),
  PRIMARY KEY (project_no),
  CONSTRAINT fk_prj_status FOREIGN KEY (status) REFERENCES status (status),
  CONSTRAINT fk_prj_sector FOREIGN KEY (busns_sector) REFERENCES busns_sector (busns_sector)
);
CREATE INDEX idx_prj_status ON projects (status);
CREATE INDEX idx_prj_sector ON projects (busns_sector);

CREATE TABLE ts_dtl (
  td_id          BIGINT GENERATED ALWAYS AS IDENTITY,
  emp_no         VARCHAR(20) NOT NULL,
  week_no        INT NOT NULL,
  ts_date        DATE NOT NULL,
  rglr_hrs       DECIMAL(8,2) NOT NULL DEFAULT 0.00,
  ot_hrs         DECIMAL(8,2) NOT NULL DEFAULT 0.00,
  project_no     VARCHAR(30),
  busns_unit_no  VARCHAR(20),
  nationality_no VARCHAR(10),
  dept_no        VARCHAR(20),
  branch_no      VARCHAR(20),
  PRIMARY KEY (td_id),
  CONSTRAINT fk_ts_emp     FOREIGN KEY (emp_no) REFERENCES employees (emp_no),
  CONSTRAINT fk_ts_project FOREIGN KEY (project_no) REFERENCES projects (project_no),
  CONSTRAINT fk_ts_bu      FOREIGN KEY (busns_unit_no) REFERENCES busns_unit (busns_unit_no),
  CONSTRAINT fk_ts_dept    FOREIGN KEY (dept_no) REFERENCES department (dept_no),
  CONSTRAINT fk_ts_branch  FOREIGN KEY (branch_no) REFERENCES branch (branch_no),
  CONSTRAINT fk_ts_nat     FOREIGN KEY (nationality_no) REFERENCES nations (nationality_no)
);
CREATE INDEX idx_ts_emp      ON ts_dtl (emp_no);
CREATE INDEX idx_ts_week     ON ts_dtl (week_no);
CREATE INDEX idx_ts_date     ON ts_dtl (ts_date);
CREATE INDEX idx_ts_project  ON ts_dtl (project_no);
CREATE INDEX idx_ts_bu       ON ts_dtl (busns_unit_no);
CREATE INDEX idx_ts_dept     ON ts_dtl (dept_no);
CREATE INDEX idx_ts_branch   ON ts_dtl (branch_no);
CREATE INDEX idx_ts_nat      ON ts_dtl (nationality_no);
CREATE INDEX idx_ts_billable ON ts_dtl (project_no, ts_date);

-- BILLABLE RULE
--   billable : project_no IS NOT NULL AND project_no <> ''
--   overhead : project_no IS NULL OR project_no = ''
-- Same convention carried over from MySQL: prefer NULL for overhead and
-- normalise on load. A mix of NULL and '' will silently split billable totals.

CREATE OR REPLACE VIEW v_timesheet AS
SELECT
  t.td_id, t.emp_no, e.emp_name, t.week_no, t.ts_date,
  t.rglr_hrs, t.ot_hrs, (t.rglr_hrs + t.ot_hrs) AS total_hrs,
  t.project_no, p.project_name,
  (t.project_no IS NOT NULL AND t.project_no <> '') AS is_billable,
  t.busns_unit_no, bu.clean_name AS busns_unit_name,
  t.dept_no, d.dept_dscr,
  t.branch_no, b.branch_name,
  t.nationality_no, n.country_name,
  (t.nationality_no = '1') AS is_saudi,
  p.status, st.status_dscr,
  p.busns_sector, sec.sector_dscr
FROM ts_dtl t
LEFT JOIN employees    e   ON e.emp_no         = t.emp_no
LEFT JOIN projects     p   ON p.project_no     = t.project_no
LEFT JOIN busns_unit   bu  ON bu.busns_unit_no = t.busns_unit_no
LEFT JOIN department   d   ON d.dept_no        = t.dept_no
LEFT JOIN branch       b   ON b.branch_no      = t.branch_no
LEFT JOIN nations      n   ON n.nationality_no = t.nationality_no
LEFT JOIN status       st  ON st.status        = p.status
LEFT JOIN busns_sector sec ON sec.busns_sector = p.busns_sector;

-- ── Read-only application role ──────────────────────────────────────────────
-- Claude generates SQL from free-text user questions. The application itself
-- restricts it to a single SELECT (see advisor/sql_query.py), but a DB-level
-- role restriction is the other half of defense-in-depth. Create a dedicated
-- role and put ITS connection string — not the Neon owner role's — in
-- DATABASE_URL on Render.
--
-- CREATE ROLE app_readonly LOGIN PASSWORD 'CHANGE_ME';
-- GRANT CONNECT ON DATABASE <your_db_name> TO app_readonly;
-- GRANT USAGE ON SCHEMA public TO app_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO app_readonly;
