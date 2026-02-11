VENV := .venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip

.PHONY: setup run run-file run-inline test lint check

setup:
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) src/elta_tracker.py --input-file vouchers.xlsx --input-column Voucher --output-file output/tracking_results.xlsx

run-file:
	$(PYTHON) src/elta_tracker.py --input-file config/vouchers.txt --output-file output/tracking_results.xlsx

run-inline:
	$(PYTHON) src/elta_tracker.py --vouchers NF940558640GR,NF000000001GR --output-file output/tracking_results.xlsx

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m py_compile src/elta_tracker.py tests/test_parser.py

check: lint test
