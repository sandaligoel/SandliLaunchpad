.PHONY: install run health dry-run test check verify

PYTHON ?= python3
VENV ?= .venv

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) main.py --input-json examples/sample_question.json

health:
	$(PYTHON) main.py --health

dry-run:
	DRY_RUN=true $(PYTHON) main.py --dry-run --input-json examples/sample_question.json

test:
	$(PYTHON) -m pytest tests/ -q

check:
	$(PYTHON) scripts/check_placeholders.py

verify: install check test dry-run
	$(PYTHON) -c "import main, run_workflow, config"
