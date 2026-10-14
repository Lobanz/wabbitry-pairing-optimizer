"""Phase 2 tests: doe productivity index (design §8)."""

from __future__ import annotations

from pathlib import Path

import pytest

from wabbitry_pairing_optimizer.config import ProductivityConfig, load_config
from wabbitry_pairing_optimizer.load_breeders import load_breeders
from wabbitry_pairing_optimizer.load_litters import Litter, load_litters
from wabbitry_pairing_optimizer.models import Breeder
from wabbitry_pairing_optimizer.productivity import (
    _own_score,
    doe_production_scores,
    productivity_index,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA = REPO_ROOT / "data"


@pytest.fixture(scope="module")
def roster():
    return load_breeders(DATA / "breeders.json")


@pytest.fixture(scope="module")
def litters():
    known = {b.name for b in load_breeders(DATA / "breeders.json")}
    return load_litters(DATA / "litters", known_rabbits=known)


@pytest.fixture(scope="module")
def pcfg():
    return load_config(DATA / "config.toml").productivity


def test_all_active_does_scored(roster, litters, pcfg) -> None:
    """Every active doe gets a productivity score (7 M70 + 6 TAMUK)."""
    scores = doe_production_scores(roster, litters, pcfg)
    active_does = [
        b.name for b in roster if not b.culled and not b.is_composite and b.gender == "F"
    ]
    assert set(scores) == set(active_does)
    assert len(scores) == 13
    assert all(v >= 0 for v in scores.values())


def test_betsy_is_fertile_foundation(roster, litters, pcfg) -> None:
    """Blend: betsy's rich 5-litter history anchors her daughters.

    betsy (culled) n=5 sizes [7,10,6,3,2]; her daughters kiki/lily/maxine are
    M70 does with thin own-records; their index should lean on betsy and thus be
    comparable/tied via the same mother (design §8 mother-blend).
    """
    # maxine: 0 own litters -> index == betsy's own score exactly.
    maxine = next(b for b in roster if b.name == "maxine")
    idx = productivity_index(maxine, litters, roster, pcfg)
    assert 0 < idx, "maxine should inherit betsy's positive productivity"


def test_rich_history_dominates(roster, litters, pcfg) -> None:
    """isabelle (n=6 own litters) blends only slightly toward a mother with none."""
    isabelle = next(b for b in roster if b.name == "isabelle")
    idx = productivity_index(isabelle, litters, roster, pcfg)
    # isabelle has no mother history (founder, dam=None) -> own score exactly.
    own_score = productivity_index(isabelle, litters, roster, pcfg)
    assert idx == pytest.approx(own_score, abs=1e-9)


def test_evidence_blend_fraction() -> None:
    """w_own = own_n/(own_n+K); 0-own inherits dam, thin own blends by fraction."""
    cfg = ProductivityConfig(size_weight=0.6, consistency_weight=0.4, evidence_k=2.0)
    # Synthetic dam with consistent 5-kit litters (own_score = 0.6*5 + 0.4*1 = 3.4)
    # and a doe whose own large 9-kit litter differs so the blend weight matters.
    dam = Breeder(name="mom", breed="M70 NZW", gender="F", culled=True)
    doe = Breeder(name="kid", breed="M70 NZW", gender="F", dam="mom")
    lits = [
        Litter(dam="mom", sire="s", born="2024-01-01", males=3, females=2, round="t"),
        Litter(dam="mom", sire="s", born="2024-01-02", males=3, females=2, round="t"),
        Litter(dam="kid", sire="s", born="2024-01-03", males=4, females=5, round="t"),
    ]
    roster = [dam, doe]

    # mom: sizes [5,5] -> own_score (tight, mean 5, var 0).
    mom_idx = productivity_index(dam, lits, roster, cfg)
    # kid: own score for its [9]-litter; blend with w_own = 1/(1+2) = 1/3.
    kid_own = _own_score([9.0], cfg)
    kid_idx = productivity_index(doe, lits, roster, cfg)
    assert kid_own != pytest.approx(mom_idx, abs=1e-9), "test needs distinct own/mom"
    assert kid_idx == pytest.approx((1 / 3) * kid_own + (2 / 3) * mom_idx, abs=1e-9)

    # A second doe with 2 own litters has w_own = 2/(2+2)=1/2 (more own trust).
    doe2 = Breeder(name="kid2", breed="M70 NZW", gender="F", dam="mom")
    lits2 = lits + [
        Litter(dam="kid2", sire="s", born="2024-02-01", males=3, females=2, round="t"),
        Litter(dam="kid2", sire="s", born="2024-02-02", males=2, females=3, round="t"),
    ]
    idx2 = productivity_index(doe2, lits2, roster, cfg)
    assert idx2 == pytest.approx(0.5 * _own_score([5.0, 5.0], cfg) + 0.5 * mom_idx, abs=1e-9)


def test_consistency_rewards_tight_litters() -> None:
    """Hold size fixed; tight litters (low variance) score higher than loose."""
    cfg = ProductivityConfig(size_weight=0.6, consistency_weight=0.4, evidence_k=2.0)
    tight = _own_score([4, 4, 4, 5, 5], cfg)  # mean 4.4, tight
    loose = _own_score([1, 4, 3, 7, 9], cfg)  # mean 4.8, wider spread
    # Loose has a higher mean yet still scores lower thanks to variance penalty.
    assert tight > loose, "tighter litters should score higher"
