#!/usr/bin/env bash
# Run the test suite.
# Standard project dev loop: use the project .venv (created by `uv sync`).
set -euo pipefail

.venv/bin/pytest "$@"
