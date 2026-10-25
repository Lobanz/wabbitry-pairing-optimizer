#!/usr/bin/env bash
# Run the test suite — via uv, no virtualenv required (issue #40).
# Tool versions pinned in scripts/dev-requirements.txt; uv caches the
# throwaway env. PYTHONPATH=src makes the src-layout package importable.
set -euo pipefail
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}src"
uv run --no-project --with-requirements scripts/dev-requirements.txt -- pytest "$@"
