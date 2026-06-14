.PHONY: install test lint fmt typecheck docs coverage-doc e2e check

install:
	pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check capital_cli tests

fmt:
	ruff format capital_cli tests

typecheck:
	mypy capital_cli

docs:
	typer capital_cli.cli.app utils docs --name capctl --output docs/CLI.md

coverage-doc:  ## regenerate the API coverage matrix + badge from the registry
	python tools/render_coverage.py

e2e:
	CAPCTL_E2E=1 pytest tests/e2e -m e2e -v

check: lint typecheck test
