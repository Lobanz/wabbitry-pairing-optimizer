"""Issue #36 tests: bench (exclude) breeders from a round — solver + rank + CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wabbitry_pairing_optimizer.config import load_config
from wabbitry_pairing_optimizer.load_breeders import load_breeders
from wabbitry_pairing_optimizer.load_litters import load_litters
from wabbitry_pairing_optimizer.query import rank_for_subject
from wabbitry_pairing_optimizer.solve import solve

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA = REPO_ROOT / "data"
FIXED = [("yaz", "betty"), ("yaz", "lily"), ("yaz", "kiki")]


@pytest.fixture(scope="module")
def roster():
    return load_breeders(DATA / "breeders.json")


@pytest.fixture(scope="module")
def litters(roster):
    return load_litters(DATA / "litters", known_rabbits={b.name for b in roster})


@pytest.fixture(scope="module")
def config():
    c = load_config(DATA / "config.toml")
    return c.model_copy(
        update={
            "optimization": c.optimization.model_copy(
                update={"seed": 42, "min_runs": 30, "stall_limit": 10}
            )
        }
    )


def test_solve_excludes_buck(roster, litters, config) -> None:
    """A benched buck is never auto-assigned; remaining does still covered."""
    sol = solve(roster, litters, config, fixed_pairs=FIXED, excluded={"zack"})
    assert all(p.sire != "zack" for p in sol.pairings)
    assert sol.unbred_does == []
    # The M70 auto does all land on the only remaining M70 buck (uno).
    m70_auto = {p.dam for p in sol.pairings if p.sire == "uno"}
    assert m70_auto == {"abby", "amber", "maxine", "opal"}


def test_solve_excluded_doe_not_unbred(roster, litters, config) -> None:
    """A benched doe is neither bred nor reported unbred."""
    sol = solve(roster, litters, config, fixed_pairs=FIXED, excluded={"abby"})
    assert all(p.dam != "abby" for p in sol.pairings)
    assert "abby" not in sol.unbred_does


def test_solve_excluded_in_fixed_pair_raises(roster, litters, config) -> None:
    """A fixed pair referencing a benched breeder is a contradiction (error)."""
    with pytest.raises(ValueError, match="excluded"):
        solve(roster, litters, config, fixed_pairs=[("zack", "abby")], excluded={"zack"})


def test_rank_excludes_candidates(roster, litters, config) -> None:
    """rank honors the bench list (explicit subject still works)."""
    rows = rank_for_subject("opal", "doe", roster, litters, config, excluded={"zack"})
    assert [r.sire for r in rows] == ["yaz", "uno"]


def test_cli_exclude_solve(capsys) -> None:
    """CLI --exclude benches a buck in a full solve."""
    from wabbitry_pairing_optimizer.__main__ import main

    rc = main(
        [
            str(DATA / "breeders.json"),
            "--pairs",
            str(DATA / "fixed_pairs.json"),
            "--exclude",
            "zack",
            "--config",
            str(DATA / "config.toml"),
            "--output-dir",
            str(REPO_ROOT / "tests" / "_exclude_tmp"),
        ]
    )
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["command"] == "solve"
    assert doc["unbred_does"] == []
    # Pairings live in the report artifact, not the stdout emission.
    report = json.loads((REPO_ROOT / "tests" / "_exclude_tmp" / "wabbitry-report.json").read_text())
    assert all(p["sire"] != "zack" for p in report["pairings"])


def test_cli_exclude_unknown_raises(capsys) -> None:
    """A typo in --exclude is a clean error, not a silent no-op."""
    from wabbitry_pairing_optimizer.__main__ import main

    rc = main(
        [
            str(DATA / "breeders.json"),
            "--exclude",
            "zackk",
            "--config",
            str(DATA / "config.toml"),
        ]
    )
    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["command"] == "error"
    assert "unknown breeder" in out["error"]
    assert "zackk" in out["error"]


def test_cli_rank_exclude(capsys) -> None:
    """CLI --rank honors --exclude."""
    from wabbitry_pairing_optimizer.__main__ import main

    rc = main(
        [
            str(DATA / "breeders.json"),
            "--rank",
            "doe:opal",
            "--exclude",
            "zack",
            "--config",
            str(DATA / "config.toml"),
        ]
    )
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert [r["sire"] for r in doc["rows"]] == ["yaz", "uno"]
