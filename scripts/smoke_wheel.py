"""Install a wheel into a throwaway uv tool env and exercise it.

Usage: smoke_wheel.py WHEEL

- ``uv tool install`` into per-run temp dirs (UV_TOOL_BIN_DIR / UV_TOOL_DIR) —
  the installed command never sees the repo venv.
- From a NEUTRAL cwd: ``wabbitry-pairing-optimizer --version`` must equal the
  wheel's version (proves cwd-independent install).
- From the same neutral cwd: a full solve on ABSOLUTE data paths with --seed 42
  must succeed with pairings (proves data pointing works without the repo cwd).

Exit 1 on any failure. Issue #40.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXE = "wabbitry-pairing-optimizer"


def _wheel_version(wheel: Path) -> str:
    with zipfile.ZipFile(wheel) as zf:
        meta = next(n for n in zf.namelist() if n.endswith("METADATA"))
        text = zf.read(meta).decode()
    match = re.search(r"^Version:\s*(\S+)", text, re.M)
    if match is None:
        raise SystemExit("wheel METADATA missing Version")
    return match.group(1)


def main() -> int:
    """Install the wheel into a throwaway uv env and exercise it; exit 0/1."""
    wheel = Path(sys.argv[1]).resolve()
    if not wheel.is_file():
        raise SystemExit(f"wheel not found: {wheel}")
    expect = _wheel_version(wheel)

    with tempfile.TemporaryDirectory(prefix="wab-smoke-") as td:
        tmp = Path(td)
        bin_dir = tmp / "bin"
        tool_dir = tmp / "tool"
        neutral = tmp / "cwd"
        neutral.mkdir()
        env = {**os.environ, "UV_TOOL_BIN_DIR": str(bin_dir), "UV_TOOL_DIR": str(tool_dir)}

        subprocess.run(  # noqa: S603 - our wheel, fixed argv, no shell
            ["uv", "tool", "install", str(wheel)],
            env=env,
            check=True,
            capture_output=True,  # noqa: S607 - uv resolves from PATH deliberately
        )
        exe = bin_dir / EXE

        r = subprocess.run(  # noqa: S603 - installed exe (our wheel), fixed argv, no shell
            [str(exe), "--version"], cwd=neutral, env=env, capture_output=True, text=True
        )
        if r.returncode != 0:
            raise SystemExit(f"--version failed (rc={r.returncode}): {r.stderr}")
        got = json.loads(r.stdout)["version"]
        if got != expect:
            raise SystemExit(f"installed --version {got} != wheel {expect}")

        r = subprocess.run(  # noqa: S603 - installed exe (our wheel), fixed argv, no shell
            [
                str(exe),
                str(REPO_ROOT / "data" / "breeders.json"),
                "--pairs",
                str(REPO_ROOT / "data" / "fixed_pairs.json"),
                "--config",
                str(REPO_ROOT / "data" / "config.toml"),
                "--seed",
                "42",
                "--output-dir",
                str(tmp / "art"),
            ],
            cwd=neutral,
            env=env,
            capture_output=True,
            text=True,
        )  # noqa: S603 - installed exe (our wheel), fixed argv, no shell
        if r.returncode != 0:
            raise SystemExit(f"solve failed (rc={r.returncode}): {r.stderr}")
        doc = json.loads(r.stdout)
        if doc.get("command") != "solve" or doc.get("n_pairings", 0) == 0:
            raise SystemExit(f"solve produced no pairings: {doc}")
        n = doc["n_pairings"]

    print(f"smoke OK: installed {expect}; --version from neutral cwd; solve {n} pairings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
