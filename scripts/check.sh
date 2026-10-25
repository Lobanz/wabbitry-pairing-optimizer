#!/usr/bin/env bash
# Run all static checks: format, lint, type-check — via uv, no virtualenv
# required (issue #40). Tool versions pinned in scripts/dev-requirements.txt;
# uv caches the throwaway env.
# Exits non-zero on any failure.
set -euo pipefail
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}src"
uv run --no-project --with-requirements scripts/dev-requirements.txt -- ruff format --check src tests
uv run --no-project --with-requirements scripts/dev-requirements.txt -- ruff check src tests
uv run --no-project --with-requirements scripts/dev-requirements.txt -- mypy src
