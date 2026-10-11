"""Synthetic payroll data generator — the single source of truth for every
project in this portfolio. Produces:
  - employees.csv
  - pay_periods.csv        (24 months, seeded anomalies for analytics/anomaly detection)
  - payroll_legacy.csv / payroll_target.csv   (migration pair with seeded discrepancies)
"""
import csv
import json
import random
from datetime import date, timedelta

random.seed(42)

DEPARTMENTS = ["Engineering", "Sales", "Finance", "HR", "Operations", "Support", "Marketing"]
JOB_TITLES = {
    "Engineering": ["Software Engineer", "Senior Engineer", "Engineering Manager", "QA Engineer"],
    "Sales": ["Account Executive", "Sales Manager", "SDR"],
    "Finance": ["Financial Analyst", "Accountant", "Finance Manager"],
    "HR": ["HR Generalist", "Recruiter", "HR Manager"],
    "Operations": ["Operations Analyst", "Operations Manager"],
    "Support": ["Support Engineer", "Support Lead"],
    "Marketing": ["Marketing Analyst", "Marketing Manager"],
}
SALARY_BANDS = {
    "Software Engineer": (75000, 115000), "Senior Engineer": (115000, 155000),
    "Engineering Manager": (140000, 180000), "QA Engineer": (65000, 95000),
    "Account Executive": (60000, 110000), "Sales Manager": (90000, 140000), "SDR": (50000, 70000),
    "Financial Analyst": (65000, 95000), "Accountant": (55000, 80000), "Finance Manager": (95000, 130000),
    "HR Generalist": (55000, 80000), "Recruiter": (55000, 85000), "HR Manager": (90000, 120000),
    "Operations Analyst": (55000, 85000), "Operations Manager": (90000, 125000),
    "Support Engineer": (55000, 85000), "Support Lead": (80000, 110000),
    "Marketing Analyst": (55000, 85000), "Marketing Manager": (90000, 125000),
}
LOCATIONS = ["New York", "Austin", "Remote", "San Francisco", "Chicago", "Denver"]
FIRST = ["James", "Maria", "Liam", "Sofia", "Noah", "Emma", "Ethan", "Olivia", "Lucas", "Ava",
         "Mason", "Mia", "Logan", "Zoe", "Aiden", "Grace", "Carter", "Lily", "Wyatt", "Chloe"]
LAST = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez",
        "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Taylor", "Thomas", "Moore"]

N_EMPLOYEES = 400
employees = []
for i in range(1, N_EMPLOYEES + 1):
    dept = random.choice(DEPARTMENTS)
    title = random.choice(JOB_TITLES[dept])
    lo, hi = SALARY_BANDS[title]
    base_salary = round(random.uniform(lo, hi), 2)
    hire_date = date(2021, 1, 1) + timedelta(days=random.randint(0, 1400))
    terminated = random.random() < 0.12
    term_date = ""
    if terminated:
        td = hire_date + timedelta(days=random.randint(90, 1200))
        if td < date(2025, 1, 1):
            term_date = td.isoformat()
    employees.append({
        "employee_id": f"E{i:04d}",
        "name": f"{random.choice(FIRST)} {random.choice(LAST)}",
        "department": dept,
        "job_title": title,
        "location": random.choice(LOCATIONS),
        "hire_date": hire_date.isoformat(),
        "termination_date": term_date,
        "salary_band": f"{title} ({lo//1000}k-{hi//1000}k)",
        "base_salary": base_salary,
    })

with open("employees.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(employees[0].keys()))
    w.writeheader()
    w.writerows(employees)

# ---- pay_periods.csv (24 months, seeded anomalies) ----
PERIODS = [f"2023-{m:02d}" for m in range(1, 13)] + [f"2024-{m:02d}" for m in range(1, 13)]
jump_employees = set(random.sample(range(1, N_EMPLOYEES + 1), 15))
dup_targets = set(random.sample(range(1, N_EMPLOYEES + 1), 10))
ot_outlier_targets = set(random.sample(range(1, N_EMPLOYEES + 1), 12))

# Ground truth for eval (which employees were deliberately seeded as anomalous) —
# consumed by the anomaly-detection projects' eval scripts to compute precision/recall/F1.
with open("ground_truth.json", "w") as f:
    json.dump({
        "jump_employees": sorted(jump_employees),
        "dup_targets": sorted(dup_targets),
        "ot_outlier_targets": sorted(ot_outlier_targets),
    }, f)

rows = []
for emp in employees:
    emp_id = emp["employee_id"]
    idx = int(emp_id[1:])
    hire = date.fromisoformat(emp["hire_date"])
    term = date.fromisoformat(emp["termination_date"]) if emp["termination_date"] else None
    monthly_base = round(emp["base_salary"] / 12, 2)
    jump_at = random.randint(10, 18) if idx in jump_employees else None
    for pi, period in enumerate(PERIODS):
        period_date = date(int(period[:4]), int(period[5:7]), 1)
        if period_date < hire or (term and period_date > term):
            continue
        gross = monthly_base
        if jump_at is not None and pi >= jump_at:
            gross = round(monthly_base * random.uniform(1.4, 1.9), 2)  # unexplained jump
        ot_hours = round(max(0, random.gauss(5, 4)), 1)
        if idx in ot_outlier_targets and random.random() < 0.3:
            ot_hours = round(random.uniform(40, 70), 1)  # OT outlier
        ot_pay = round(ot_hours * (monthly_base / 160) * 1.5, 2)
        deductions = round(gross * 0.22, 2)
        bonus = round(gross * 0.05, 2) if random.random() < 0.1 else 0.0
        net = round(gross + ot_pay + bonus - deductions, 2)
        rows.append({
            "employee_id": emp_id, "pay_period": period, "gross_pay": gross,
            "overtime_hours": ot_hours, "overtime_pay": ot_pay, "deductions": deductions,
            "bonus": bonus, "net_pay": net,
        })
        if idx in dup_targets and pi == 5:
            dup = dict(rows[-1])
            rows.append(dup)  # duplicate payment in same period

with open("pay_periods.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

# ---- payroll_legacy.csv / payroll_target.csv (migration pair) ----
latest_period_rows = [r for r in rows if r["pay_period"] == "2024-12"]
legacy_rows, target_rows = [], []
missing_field_targets = set(random.sample(range(len(latest_period_rows)), 15))
mismatch_targets = set(random.sample(range(len(latest_period_rows)), 10))
dup_in_legacy = set(random.sample(range(len(latest_period_rows)), 8))
missing_in_target = set(random.sample(range(len(latest_period_rows)), 5))

for i, r in enumerate(latest_period_rows):
    emp = next(e for e in employees if e["employee_id"] == r["employee_id"])
    legacy = {
        "employee_id": r["employee_id"], "name": emp["name"], "department": emp["department"],
        "bank_account": f"ACC{random.randint(100000,999999)}", "gross_pay": r["gross_pay"],
        "net_pay": r["net_pay"],
    }
    target = dict(legacy)
    if i in missing_field_targets:
        target["bank_account"] = ""  # missing required field after migration
    if i in mismatch_targets:
        target["net_pay"] = round(target["net_pay"] + random.choice([-50, 25, 100, -12.5]), 2)
    legacy_rows.append(legacy)
    if i in dup_in_legacy:
        legacy_rows.append(dict(legacy))  # duplicate in legacy export
    if i not in missing_in_target:
        target_rows.append(target)

with open("payroll_legacy.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(legacy_rows[0].keys()))
    w.writeheader(); w.writerows(legacy_rows)
with open("payroll_target.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(target_rows[0].keys()))
    w.writeheader(); w.writerows(target_rows)

print(f"employees={len(employees)} pay_periods={len(rows)} legacy={len(legacy_rows)} target={len(target_rows)}")
