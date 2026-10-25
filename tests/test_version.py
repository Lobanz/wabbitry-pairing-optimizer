"""Package version is single-sourced (issue #40, PR A)."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import wabbitry_pairing_optimizer as pkg
from wabbitry_pairing_optimizer.__main__ import main

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_version_is_semver() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", pkg.__version__)


def test_cli_version_emits_package_version(capsys) -> None:
    """--version emits the package __version__ (one source of truth)."""
    assert main(["--version"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["command"] == "version"
    assert out["version"] == pkg.__version__


def test_hatch_reads_version_from_package() -> None:
    """pyproject points hatch at the single source (no static copy to drift)."""
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["dynamic"] == ["version"]
    assert pyproject["tool"]["hatch"]["version"]["path"] == (
        "src/wabbitry_pairing_optimizer/__init__.py"
    )
