#!/usr/bin/env bash
# Run all static checks: format, lint, type-check.
# Standard project dev loop: use the project .venv (created by `uv sync`).
# Exits non-zero on any failure.
set -euo pipefail

.venv/bin/ruff format --check src tests
.venv/bin/ruff check src tests
.venv/bin/mypy src
