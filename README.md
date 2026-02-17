# ELTA Tracking Pipeline

## What This Project Does

This project tracks courier voucher IDs and exports shipment history into structured files.

It reads vouchers from inline input or a file, requests tracking events, and writes outputs as Excel or CSV (including summary tables).

## Why It Was Built

It was built to automate repetitive shipment-status checks and produce consistent, shareable tracking outputs for operational reporting.

## Tech Stack

- Python 3
- requests
- pandas
- openpyxl
- urllib3
- pytest

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## How To Run

```bash
python src/elta_tracker.py --vouchers NF940558640GR,NF123456789GR --output-file output/tracking_results.xlsx
```

Or with an input file:

```bash
python src/elta_tracker.py --input-file vouchers.xlsx --input-column Voucher --output-file output/tracking_results.xlsx
```

## Configuration

This project does not require a dedicated config file.

Runtime behavior is configured via CLI arguments, including:
- input source and voucher column
- output format/path
- request timeout/retries/backoff/delay
- optional markdown summary output path
