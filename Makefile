.PHONY: install run health dry-run test check verify

PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python

install:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run:
	$(PY) main.py --file examples/sample_kyc_document.txt

health:
	$(PY) main.py --health

dry-run:
	$(PY) main.py --dry-run

test:
	$(PY) -m pytest tests/ -q

check:
	$(PY) scripts/check_placeholders.py

verify: check test dry-run
	$(PY) -c "import main, run_workflow, config; print('imports ok')"
