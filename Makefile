# hw-registry developer Makefile.
#
# Usage:
#   make help        # list targets
#   make install     # set up venv, dev deps, pre-commit hooks
#   make schema      # regenerate schemas/ from pydantic_models/
#   make validate    # run semantic validators (tools/validate.py all)
#   make test        # pytest
#   make lint        # pre-commit run --all-files
#   make fmt         # ruff format + ruff check --fix
#   make clean       # remove generated artifacts and caches

.PHONY: help install schema validate test lint fmt clean

PYTHON ?= python
UV ?= uv

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## Create venv, install dev deps, install pre-commit hooks
	$(UV) venv --python 3.12
	$(UV) pip install -e ".[dev]"
	pre-commit install

schema:  ## Regenerate JSON Schemas from Pydantic models
	$(PYTHON) -m tools.generate_schemas

validate:  ## Run all semantic validators (slug-equals-path, refs-resolve, inheritance-cycle)
	$(PYTHON) -m tools.validate all

test:  ## Run pytest
	$(PYTHON) -m pytest -q

lint:  ## Run pre-commit on every tracked file
	pre-commit run --all-files

fmt:  ## Apply ruff-format + ruff --fix
	ruff format .
	ruff check --fix .

clean:  ## Remove build / cache artifacts
	rm -rf dist/ site/ build/ .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
