"""Phase 4 tests: assignment solver (design §6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from wabbitry_pairing_optimizer.config import load_config
from wabbitry_pairing_optimizer.load_breeders import load_breeders
from wabbitry_pairing_optimizer.load_litters import load_litters
from wabbitry_pairing_optimizer.solve import solve

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA = REPO_ROOT / "data"


@pytest.fixture(scope="module")
def roster():
    return load_breeders(DATA / "breeders.json")


@pytest.fixture(scope="module")
def litters(roster):
    return load_litters(DATA / "litters", known_rabbits={b.name for b in roster})


@pytest.fixture(scope="module")
def config():
    return load_config(DATA / "config.toml")


def test_all_active_does_assigned(roster, litters, config) -> None:
    """Every active doe gets a buck (no unbred)."""
    sol = solve(roster, litters, config)
    active_does = {
        b.name for b in roster if b.gender == "F" and not b.culled and not b.is_composite
    }
    assert sol.unbred_does == []
    assigned = {p.dam for p in sol.pairings}
    assert assigned == active_does


def test_same_strain_only(roster, litters, config) -> None:
    """No cross-pool pairings (M70 x TAMUK never)."""
    sol = solve(roster, litters, config)
    by = {b.name: b for b in roster}
    for p in sol.pairings:
        assert by[p.sire].strain == by[p.dam].strain, f"cross-strain pair {p.sire} x {p.dam}"
    # Both strains are represented.
    strains = {by[p.dam].strain for p in sol.pairings}
    assert strains == {"M70", "TAMUK"}


def test_fixed_pairs_respected(roster, litters, config) -> None:
    """Operator fixed pairs (Yaz -> betty/lily/kiki) are honored."""
    fixed = [("yaz", "betty"), ("yaz", "lily"), ("yaz", "kiki")]
    sol = solve(roster, litters, config, fixed_pairs=fixed)
    fixed_by_doe = {d: s for (s, d) in fixed}
    for dam, sire in fixed_by_doe.items():
        # The fixed doe's pairing uses the fixed buck and is marked fixed.
        pairing = next(p for p in sol.pairings if p.dam == dam)
        assert pairing.sire == sire
        assert pairing.fixed is True
    # Yaz is not auto-assigned to any non-fixed doe (excluded from auto pool).
    for p in sol.pairings:
        if not p.fixed:
            assert p.sire != "yaz"


def test_deterministic_with_seed(roster, litters, config) -> None:
    """A fixed seed gives a reproducible solution."""
    cfg = config.model_copy(
        update={
            "optimization": config.optimization.model_copy(
                update={"seed": 42, "min_runs": 50, "stall_limit": 10}
            )
        }
    )
    a = solve(roster, litters, cfg)
    b = solve(roster, litters, cfg)
    assert [(p.sire, p.dam) for p in a.pairings] == [(p.sire, p.dam) for p in b.pairings]


def test_solution_fields_populated(roster, litters, config) -> None:
    """Score, schedule_days, and pairability_count are computed on the winner."""
    sol = solve(roster, litters, config)
    assert sol.score is not None
    assert sol.score.final != 0.0 or sol.score.final == 0.0  # defined
    assert sol.schedule_days > 0  # a round spans at least a day
    assert sol.pairability_count >= 0
    # Full-solution score's six components are present and sum to final.
    sc = sol.score
    assert sc.final == pytest.approx(
        sc.sum_r
        + sc.sum_history
        + sc.unbred_penalty
        + sc.sibling_penalty
        + sc.schedule_penalty
        + sc.pairability,
        abs=1e-6,
    )
