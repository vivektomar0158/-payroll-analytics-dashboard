-- Payroll Analytics views: CTEs + window functions, consumed by the Power BI semantic model.

DROP VIEW IF EXISTS v_attrition;
CREATE VIEW v_attrition AS
WITH periods AS (
  SELECT DISTINCT pay_period FROM pay_periods
)
SELECT
  p.pay_period,
  SUM(CASE WHEN e.termination_date IS NOT NULL AND e.termination_date != ''
           AND substr(e.termination_date,1,7) = p.pay_period THEN 1 ELSE 0 END) AS terminations,
  COUNT(DISTINCT e.employee_id) AS headcount
FROM periods p
LEFT JOIN employees e ON e.hire_date <= p.pay_period || '-28'
GROUP BY p.pay_period
ORDER BY p.pay_period;

DROP VIEW IF EXISTS v_salary_rank;
CREATE VIEW v_salary_rank AS
SELECT
  employee_id, department, job_title, base_salary,
  RANK() OVER (PARTITION BY department ORDER BY base_salary DESC) AS dept_salary_rank,
  AVG(base_salary) OVER (PARTITION BY department) AS dept_avg_salary,
  base_salary - AVG(base_salary) OVER (PARTITION BY department) AS delta_from_dept_avg
FROM employees;

DROP VIEW IF EXISTS v_overtime_rolling;
CREATE VIEW v_overtime_rolling AS
SELECT
  employee_id, pay_period, overtime_hours, overtime_pay,
  AVG(overtime_hours) OVER (
    PARTITION BY employee_id ORDER BY pay_period
    ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
  ) AS rolling_3mo_avg_ot_hours,
  SUM(overtime_pay) OVER (PARTITION BY pay_period) AS total_ot_cost_period
FROM pay_periods;

DROP VIEW IF EXISTS v_cohort_retention;
CREATE VIEW v_cohort_retention AS
WITH cohorts AS (
  SELECT employee_id, substr(hire_date,1,4) AS hire_year, termination_date
  FROM employees
)
SELECT
  hire_year,
  COUNT(*) AS cohort_size,
  SUM(CASE WHEN termination_date IS NULL OR termination_date = '' THEN 1 ELSE 0 END) AS still_active,
  ROUND(100.0 * SUM(CASE WHEN termination_date IS NULL OR termination_date = '' THEN 1 ELSE 0 END) / COUNT(*), 1) AS retention_pct
FROM cohorts
GROUP BY hire_year
ORDER BY hire_year;
