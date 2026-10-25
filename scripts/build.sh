#!/usr/bin/env bash
# Build + verify the wheel (issue #40): full gate -> uv build -> check -> smoke.
# Usage: scripts/build.sh [--expect X.Y.Z]
# A local build needs no venv setup beyond `uv sync`; uv owns packaging.
set -euo pipefail

EXPECT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --expect) EXPECT="${2:?--expect needs a version}"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

bash scripts/check.sh
bash scripts/test.sh
uv build --wheel --out-dir dist

VERSION="$(.venv/bin/python -c 'from wabbitry_pairing_optimizer import __version__; print(__version__)')"
WHEEL="dist/wabbitry_pairing_optimizer-${VERSION}-py3-none-any.whl"
if [ ! -f "$WHEEL" ]; then
  echo "wheel not found: $WHEEL" >&2
  exit 1
fi

ARGS=("$WHEEL")
if [ -n "$EXPECT" ]; then
  ARGS+=(--expect "$EXPECT")
fi
.venv/bin/python scripts/check_wheel.py "${ARGS[@]}"
.venv/bin/python scripts/smoke_wheel.py "$WHEEL"
echo "BUILD OK: $WHEEL"
