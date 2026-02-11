# ELTA Tracking Pipeline

Python CLI tool that tracks ELTA Courier vouchers and exports shipment events to Excel/CSV plus a non-technical summary report.

## Why this project matters
- Converts a repetitive manual task into a reproducible pipeline.
- Handles transient errors with retries/backoff and request timeouts.
- Produces structured output for reporting and operations teams.
- Supports scheduled execution and artifact delivery for non-technical stakeholders.

## Setup
```bash
cd /Users/chatzigrigorioug.a/myproject/elta-tracking-pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage
### 1) Run with inline vouchers
```bash
python3 src/elta_tracker.py \
  --vouchers NF940558640GR,NF123456789GR \
  --output-file output/tracking_results.xlsx
```

### 2) Run with input file
```bash
python3 src/elta_tracker.py \
  --input-file vouchers.xlsx \
  --input-column Voucher \
  --output-file output/tracking_results.xlsx \
  --summary-markdown output/tracking_summary.md
```

Supported input formats:
- `.xlsx`
- `.csv`
- `.txt` (one voucher per line)

## Makefile shortcuts
```bash
make setup
cp config/vouchers.sample.txt config/vouchers.txt
make run-file
make run-inline
make test
make lint
make check
```

## Output
If output is `.xlsx`, the file includes 3 sheets:
- `events`
- `latest_status`
- `status_counts`

If output is `.csv`, additional files are generated automatically:
- `<name>_latest_status.csv`
- `<name>_status_counts.csv`

Optional markdown summary (for non-tech stakeholders):
- `output/tracking_summary.md`

Event schema:
- `Voucher`
- `Status`
- `Date`
- `Time`
- `Location`

## Scheduling
### Cron example
```bash
0 9 * * * cd /Users/chatzigrigorioug.a/myproject/elta-tracking-pipeline && .venv/bin/python3 src/elta_tracker.py --input-file vouchers.xlsx --input-column Voucher --output-file output/tracking_results.xlsx
```

### GitHub Actions schedule
- Workflow: `.github/workflows/scheduled-tracking.yml`
- Runs daily on a UTC cron and can be triggered manually.
- Uploads `output/*` as workflow artifacts.

Required secret:
- `ELTA_VOUCHERS`: comma-separated vouchers, e.g. `NF940558640GR,NF123456789GR`

### Airflow / n8n note
This CLI can be wrapped by:
- Airflow (`BashOperator` or `PythonOperator`)
- n8n (`Execute Command` node running the CLI)

## Legal and Responsible Use
- Use the tool only for vouchers your organization is authorized to process.
- Respect ELTA website/API terms of use and rate limits.
- Do not use aggressive concurrency or request flooding.
- Avoid storing or publishing personal data in repository files, logs, or artifacts.
- Keep real voucher lists in local files or secrets (`config/vouchers.txt`, `ELTA_VOUCHERS`), never in git.

This project is provided for educational and internal process automation purposes.

## Testing
```bash
pytest -q
```
