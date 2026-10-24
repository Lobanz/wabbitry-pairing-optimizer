"""CLI error-path tests (issue #27).

Known failure modes (bad config, missing/broken data) emit a clean error;
UNEXPECTED errors must surface the root cause (type + traceback) instead of
being swallowed by a broad catch.
"""

from __future__ import annotations

import json
from pathlib import Path

from wabbitry_pairing_optimizer.__main__ import main

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA = REPO_ROOT / "data"


def test_known_error_clean_json(capsys) -> None:
    """A known failure (missing breeders file) emits a clean error dict."""
    rc = main([str(DATA / "does-not-exist.json")])
    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["command"] == "error"
    assert "error" in out
    # Known failures are concise: no traceback, not flagged unexpected.
    assert out.get("unexpected") is None
    assert "traceback" not in out


def test_known_error_clean_text(capsys) -> None:
    """Text-mode known failure is a plain message, no traceback dump."""
    rc = main(["--output", "text", str(DATA / "does-not-exist.json")])
    assert rc == 1
    out = capsys.readouterr().out
    assert "error" in out
    assert "Traceback" not in out


def test_unexpected_error_surfaces_traceback(capsys, monkeypatch) -> None:
    """An unexpected error includes type + traceback (root cause not hidden)."""
    import importlib

    def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    # importlib.import_module returns the real module from sys.modules — the
    # package's __init__ re-export shadows `solve` as a function attribute, so
    # neither `import ... as` nor monkeypatch's string form resolve the module.
    solve_mod = importlib.import_module("wabbitry_pairing_optimizer.solve")
    monkeypatch.setattr(solve_mod, "solve", _boom)
    rc = main([str(DATA / "breeders.json")])
    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["command"] == "error"
    assert out["unexpected"] is True
    assert out["type"] == "RuntimeError"
    assert "boom" in out["error"]
    assert "Traceback" in out["traceback"]
