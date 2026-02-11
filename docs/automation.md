# Automation Patterns

## 1) GitHub Actions (quick win)
- Use `.github/workflows/scheduled-tracking.yml`.
- Store vouchers in repository secret `ELTA_VOUCHERS`.
- Download artifacts (`tracking_results.xlsx`, `tracking_summary.md`) from each run.

## 2) Airflow (team-grade orchestration)
Use a DAG task that executes:

```python
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG(
    dag_id="elta_tracking_daily",
    start_date=datetime(2025, 1, 1),
    schedule="0 6 * * *",
    catchup=False,
) as dag:
    run_tracker = BashOperator(
        task_id="run_tracker",
        bash_command=(
            "cd /path/to/elta-tracking-pipeline && "
            ".venv/bin/python3 src/elta_tracker.py "
            "--input-file config/vouchers.txt "
            "--output-file output/tracking_results.xlsx "
            "--summary-markdown output/tracking_summary.md"
        ),
    )
```

## 3) n8n (no-code friendly)
Suggested flow:
1. `Cron` node (daily)
2. `Execute Command` node:
   - command: `python3 src/elta_tracker.py --input-file config/vouchers.txt --output-file output/tracking_results.xlsx --summary-markdown output/tracking_summary.md`
3. Optional:
   - `Read Binary File` (excel or markdown)
   - `Email` / `Slack` node for stakeholder delivery
