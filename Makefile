.PHONY: install run health dry-run test check verify

install:
	python -m pip install -r requirements.txt

run:
	python main.py --file examples/sample_kyc.txt

health:
	python main.py --health

dry-run:
	python main.py --dry-run

test:
	python -m pytest tests/ -q

check:
	python scripts/check_placeholders.py

verify: install check test dry-run
