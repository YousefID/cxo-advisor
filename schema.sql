-- ZFP Advisor — MySQL schema
-- Translated from the Power BI semantic model in backend/advisor.py
-- Target: Cloud SQL for MySQL 8.0, me-central1 (Doha)
-- STRUCTURE ONLY. No rows. See SCHEMA.md for seeding guidance.

CREATE DATABASE IF NOT EXISTS zfp_advisor
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE zfp_advisor;

CREATE TABLE nations (
  nationality_no VARCHAR(10) NOT NULL,
  country_name   VARCHAR(120) NOT NULL,
  PRIMARY KEY (nationality_no)
) ENGINE=InnoDB;

CREATE TABLE branch (
  branch_no   VARCHAR(20) NOT NULL,
  branch_name VARCHAR(120) NOT NULL,
  PRIMARY KEY (branch_no)
) ENGINE=InnoDB;

CREATE TABLE department (
  dept_no   VARCHAR(20) NOT NULL,
  dept_dscr VARCHAR(160) NOT NULL,
  PRIMARY KEY (dept_no)
) ENGINE=InnoDB;

CREATE TABLE busns_unit (
  busns_unit_no VARCHAR(20) NOT NULL,
  clean_name    VARCHAR(160) NOT NULL,
  PRIMARY KEY (busns_unit_no)
) ENGINE=InnoDB;

CREATE TABLE status (
  status      VARCHAR(20) NOT NULL,
  status_dscr VARCHAR(120) NOT NULL,
  PRIMARY KEY (status)
) ENGINE=InnoDB;

CREATE TABLE busns_sector (
  busns_sector VARCHAR(20) NOT NULL,
  sector_dscr  VARCHAR(160) NOT NULL,
  PRIMARY KEY (busns_sector)
) ENGINE=InnoDB;

CREATE TABLE employees (
  emp_no         VARCHAR(20) NOT NULL,
  emp_name       VARCHAR(200) NULL,
  dept_no        VARCHAR(20) NULL,
  branch_no      VARCHAR(20) NULL,
  busns_unit_no  VARCHAR(20) NULL,
  nationality_no VARCHAR(10) NULL,
  PRIMARY KEY (emp_no),
  KEY idx_emp_dept (dept_no),
  KEY idx_emp_branch (branch_no),
  KEY idx_emp_bu (busns_unit_no),
  KEY idx_emp_nat (nationality_no),
  CONSTRAINT fk_emp_dept   FOREIGN KEY (dept_no) REFERENCES department (dept_no),
  CONSTRAINT fk_emp_branch FOREIGN KEY (branch_no) REFERENCES branch (branch_no),
  CONSTRAINT fk_emp_bu     FOREIGN KEY (busns_unit_no) REFERENCES busns_unit (busns_unit_no),
  CONSTRAINT fk_emp_nat    FOREIGN KEY (nationality_no) REFERENCES nations (nationality_no)
) ENGINE=InnoDB;

CREATE TABLE projects (
  project_no   VARCHAR(30) NOT NULL,
  project_name VARCHAR(255) NULL,
  status       VARCHAR(20) NULL,
  busns_sector VARCHAR(20) NULL,
  PRIMARY KEY (project_no),
  KEY idx_prj_status (status),
  KEY idx_prj_sector (busns_sector),
  CONSTRAINT fk_prj_status FOREIGN KEY (status) REFERENCES status (status),
  CONSTRAINT fk_prj_sector FOREIGN KEY (busns_sector) REFERENCES busns_sector (busns_sector)
) ENGINE=InnoDB;

CREATE TABLE ts_dtl (
  td_id          BIGINT NOT NULL AUTO_INCREMENT,
  emp_no         VARCHAR(20) NOT NULL,
  week_no        INT NOT NULL,
  ts_date        DATE NOT NULL,
  rglr_hrs       DECIMAL(8,2) NOT NULL DEFAULT 0.00,
  ot_hrs         DECIMAL(8,2) NOT NULL DEFAULT 0.00,
  project_no     VARCHAR(30) NULL,
  busns_unit_no  VARCHAR(20) NULL,
  nationality_no VARCHAR(10) NULL,
  dept_no        VARCHAR(20) NULL,
  branch_no      VARCHAR(20) NULL,
  PRIMARY KEY (td_id),
  KEY idx_ts_emp (emp_no),
  KEY idx_ts_week (week_no),
  KEY idx_ts_date (ts_date),
  KEY idx_ts_project (project_no),
  KEY idx_ts_bu (busns_unit_no),
  KEY idx_ts_dept (dept_no),
  KEY idx_ts_branch (branch_no),
  KEY idx_ts_nat (nationality_no),
  KEY idx_ts_billable (project_no, ts_date),
  CONSTRAINT fk_ts_emp     FOREIGN KEY (emp_no) REFERENCES employees (emp_no),
  CONSTRAINT fk_ts_project FOREIGN KEY (project_no) REFERENCES projects (project_no),
  CONSTRAINT fk_ts_bu      FOREIGN KEY (busns_unit_no) REFERENCES busns_unit (busns_unit_no),
  CONSTRAINT fk_ts_dept    FOREIGN KEY (dept_no) REFERENCES department (dept_no),
  CONSTRAINT fk_ts_branch  FOREIGN KEY (branch_no) REFERENCES branch (branch_no),
  CONSTRAINT fk_ts_nat     FOREIGN KEY (nationality_no) REFERENCES nations (nationality_no)
) ENGINE=InnoDB;

-- BILLABLE RULE
--   billable : project_no IS NOT NULL AND project_no <> ''
--   overhead : project_no IS NULL OR project_no = ''
-- Power BI stored overhead as a blank string. Prefer NULL here and normalise on
-- load. A mix of NULL and '' will silently split billable totals.

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
