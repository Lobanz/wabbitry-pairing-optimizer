#!/usr/bin/env bash
# Run the test suite.
# Used by pre-push hook; humans run this locally before push.
# Exits non-zero on any failure.
set -euo pipefail

pytest
