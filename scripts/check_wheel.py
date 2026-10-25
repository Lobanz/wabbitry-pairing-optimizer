"""Verify a built wheel: package content present + version matches.

Usage: check_wheel.py WHEEL [--expect X.Y.Z]

Refuses (exit 1) if any source module is missing from the wheel, the console
entry point is absent, or the version is wrong (against --expect when given,
and always against the package's own __version__, so a release can't ship the
wrong wheel). Issue #40.
"""

from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PKG = "wabbitry_pairing_optimizer"
SRC_PKG = REPO_ROOT / "src" / PKG


def main() -> int:
    """Verify the wheel and exit 0/1."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--expect", help="the version this wheel must carry")
    args = parser.parse_args()
    if not args.wheel.is_file():
        raise SystemExit(f"wheel not found: {args.wheel}")

    with zipfile.ZipFile(args.wheel) as zf:
        names = set(zf.namelist())

        missing = [
            f"{PKG}/{p.name}"
            for p in sorted(SRC_PKG.glob("*.py"))
            if f"{PKG}/{p.name}" not in names
        ]
        if missing:
            raise SystemExit(f"wheel missing source modules: {missing}")

        entry = next((n for n in names if n.endswith("entry_points.txt")), None)
        if entry is None or "wabbitry-pairing-optimizer" not in zf.read(entry).decode():
            raise SystemExit("wheel missing the console entry point")

        meta = next((n for n in names if n.endswith("METADATA")), None)
        if meta is None:
            raise SystemExit("wheel missing METADATA")
        text = zf.read(meta).decode()
        version = re.search(r"^Version:\s*(\S+)", text, re.M)
        if version is None:
            raise SystemExit("METADATA missing Version")
        version = version.group(1)

    from wabbitry_pairing_optimizer import __version__ as pkg_version

    if version != pkg_version:
        raise SystemExit(f"METADATA version {version} != package {pkg_version}")
    if args.expect and version != args.expect:
        raise SystemExit(f"wheel version {version} != expected {args.expect}")

    print(f"wheel OK: {args.wheel.name} v{version} ({len(names)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
