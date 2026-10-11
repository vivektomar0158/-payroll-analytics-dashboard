# Payroll Analytics Dashboard

**400 employees, 6.2% attrition, $90.5K average salary, $2.81M total overtime spend (5.2% of gross pay) across 24 months of pay periods; recommended a closer look at departments driving that OT share before the next budget cycle.**

Power BI + SQL analytics covering attrition, salary bands, overtime cost, and hire-year cohorts for a synthetic 400-employee payroll dataset (24 months of pay periods).

## Data

`data/generate_data.py` generates `employees.csv` and `pay_periods.csv` (seeded with salary jumps, duplicate payments, and OT outliers — reused by the Anomaly Detection project) and loads them into `data/payroll.db` (SQLite). Regenerate with:

```
cd data && python generate_data.py
```

## SQL layer

`sql/views.sql` defines four views using CTEs and window functions:
- `v_attrition` — monthly headcount/termination counts
- `v_salary_rank` — `RANK()`/`AVG() OVER (PARTITION BY department)` for pay-equity analysis
- `v_overtime_rolling` — 3-month rolling OT average per employee (`ROWS BETWEEN 2 PRECEDING AND CURRENT ROW`) + total OT cost per period
- `v_cohort_retention` — retention % by hire-year cohort

Apply with: `python -c "import sqlite3; sqlite3.connect('data/payroll.db').executescript(open('sql/views.sql').read())"`

## Power BI report (PBIP project — authored as text, not built by hand in the GUI)

This repo contains a **Power BI Project** (`PayrollAnalytics.pbip`), the enhanced text-based format:
- `PayrollAnalytics.SemanticModel/` — TMDL tables (`Employees`, `PayPeriods`), a relationship, and DAX measures (`Headcount`, `Attrition Rate`, `Average Salary`, `Total OT Cost`, `OT Cost %`, `YoY Gross Pay Growth`), fully scripted.
- `PayrollAnalytics.Report/` — four scaffolded pages in the right order (Overview, Attrition & Cohorts, Salary Bands, Overtime Cost).

Note: `Power Query`'s `File.Contents()` requires an **absolute** path, so the two table definitions (`PayrollAnalytics.SemanticModel/definition/tables/*.tmdl`) hardcode this machine's path to `data/employees.csv` / `data/pay_periods.csv`. If you move this project to a different machine or folder, update those two `File.Contents("...")` paths to match.

### To open it

1. Power BI Desktop → **File → Options and settings → Options → Preview features** → enable **"Power BI Project (.pbip) save option"** and **"Store reports using enhanced metadata format (PBIR)"**. Restart Desktop.
2. Open `PayrollAnalytics.pbip`. The semantic model loads automatically from the CSVs (relative paths — keep `data/*.csv` alongside the project) with all measures already defined.
3. The four pages exist but are empty canvases — visuals weren't hand-authored in JSON (that part of the PBIR schema is too version-fragile to script blindly without validating in Desktop). Add visuals per page, ~15 min total:
   - **Overview**: 3 cards → `Headcount`, `Active Headcount`, `Attrition Rate`
   - **Attrition & Cohorts**: line chart of `v_attrition` (headcount/terminations by pay_period) + bar chart of `v_cohort_retention` (retention_pct by hire_year)
   - **Salary Bands**: bar chart of `v_salary_rank` (base_salary by department, sorted by dept_salary_rank) + table showing delta_from_dept_avg
   - **Overtime Cost**: line chart of `rolling_3mo_avg_ot_hours` over pay_period + bar chart of `Total OT Cost` by department
4. Publish to the Power BI Service or export screenshots for the portfolio.
