#!/usr/bin/env bash
# Local release, no CI (issue #40): the operator tags vX.Y.Z on main
# (ESL tags-follow-semver), then this verifies the tag, builds with
# --expect, and attaches the wheel to a GitHub Release.
# Usage: scripts/release.sh vX.Y.Z     (requires GH_TOKEN with repo scope)
set -euo pipefail

VERSION="${1:?usage: scripts/release.sh vX.Y.Z}"

case "$VERSION" in
  v[0-9]*.[0-9]*.[0-9]*) ;;
  *) echo "version must look like vX.Y.Z — got $VERSION" >&2; exit 2 ;;
esac

if [ "$(git describe --tags --exact-match 2>/dev/null || true)" != "$VERSION" ]; then
  echo "HEAD is not the exact tag $VERSION — tag main first:" >&2
  echo "  git tag $VERSION && git push origin $VERSION" >&2
  exit 1
fi

bash scripts/build.sh --expect "${VERSION#v}"

WHEEL="dist/wabbitry_pairing_optimizer-${VERSION#v}-py3-none-any.whl"
if [ ! -f "$WHEEL" ]; then
  echo "wheel not found: $WHEEL" >&2
  exit 1
fi

gh release create "$VERSION" "$WHEEL" --title "$VERSION" --notes "See CHANGELOG.md for $VERSION."
echo "RELEASED: $VERSION ($WHEEL)"
