"""Phase 1 tests: data loading, recipe verification, and kinship r (ADR 0003).

Validates the genetic core against the ADR 0003 anchor values computed by hand
during design, the corrected sibling-derivation rule, and the real roster.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from wabbitry_pairing_optimizer.config import load_config
from wabbitry_pairing_optimizer.kinship import (
    PairTier,
    coancestry_matrix_r,
    full_sibling_sets,
    relationship_kind,
    tier_for_pair,
    tier_for_r,
)
from wabbitry_pairing_optimizer.load_breeders import load_breeders
from wabbitry_pairing_optimizer.recipe import verify_recipes

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA = REPO_ROOT / "data"


def _pair(a: str, b: str) -> tuple[str, str]:
    """Return ``(a, b)`` in the matrix's canonical (sorted) order."""
    return (a, b) if a < b else (b, a)


@pytest.fixture(scope="module")
def roster():
    return load_breeders(DATA / "breeders.json")


@pytest.fixture(scope="module")
def kinship():
    cfg = load_config(DATA / "config.toml")
    return cfg.kinship


def test_load_breeders_integrity(roster) -> None:
    """The real 28-rabbit roster loads and validates."""
    assert len(roster) == 28
    names = [b.name for b in roster]
    assert len(set(names)) == 28


def test_recipe_verification_no_drift(roster) -> None:
    """Stored recipes match the half-parent pedigree derivation (or list drift)."""
    drifters = verify_recipes(roster)
    assert drifters == [], f"recipes drift for: {drifters}"


def test_self_r_is_one(roster, kinship) -> None:
    """Sanity: distinct-pair matrix has full-sib=0.5 and outcross=0 (self implied 1)."""
    mat = coancestry_matrix_r(roster, kinship)
    # Self-pairs aren't emitted (distinct only); full-sib and outcross set the scale.
    assert mat[_pair("betty", "lily")] == pytest.approx(0.5, abs=1e-9)
    assert mat[_pair("yaz", "betty")] == pytest.approx(0.0, abs=1e-9)


def test_adr_0003_anchors(roster, kinship) -> None:
    """Hand-verified anchors from ADR 0003 (S=0.5 default)."""
    assert kinship.sister_factor == 0.5
    mat = coancestry_matrix_r(roster, kinship)
    checks = {
        ("betty", "lily"): 0.5,  # full sibs
        ("betty", "kiki"): 0.5,  # full sibs
        ("abigail", "betsy"): 0.5,  # founder sisters -> S=0.5
        ("yaz", "betty"): 0.0,  # outcross
    }
    for pair, expected in checks.items():
        got = mat.get(_pair(*pair))
        assert got is not None, f"missing pair {pair} from matrix"
        assert got == pytest.approx(expected, abs=1e-9), f"r{pair} = {got}, expected {expected}"
    # betty x abby = 0.25 -> 0.375 at S=0.5 (cousins via sister-founders)
    assert mat[_pair("abby", "betty")] == pytest.approx(0.375, abs=1e-9)


def test_no_distinct_exceeds_half(roster, kinship) -> None:
    """No pair of distinct rabbits has r above 0.5 (design §5 ceiling)."""
    mat = coancestry_matrix_r(roster, kinship)
    for (a, b), r in mat.items():
        assert r <= 0.5 + 1e-9, f"r({a},{b})={r} exceeds 0.5"
        assert r >= 0.0, f"negative r({a},{b})={r}"


def test_founder_relationships(roster, kinship) -> None:
    """A founder is unrelated to everything except descendants.

    Regression test: the founder→nonfounder recursion branch must use factor
    0.5 (not 0.25), so parent-offspring r = 0.5. isabelle is a founder (dam of
    vader & xerces, mate of willy).
    """
    mat = coancestry_matrix_r(roster, kinship)
    # Founder parents: unrelated to their mate/themselves-equals-nothing.
    assert mat[_pair("isabelle", "willy")] == pytest.approx(0.0, abs=1e-9)
    assert mat[_pair("willy", "yaz")] == pytest.approx(0.0, abs=1e-9)
    # Founder parent→offspring = 0.5 (parent-offspring, normal line-breeding).
    assert mat[_pair("isabelle", "vader")] == pytest.approx(0.5, abs=1e-9)
    assert mat[_pair("isabelle", "xerces")] == pytest.approx(0.5, abs=1e-9)
    assert mat[_pair("willy", "vader")] == pytest.approx(0.5, abs=1e-9)
    assert mat[_pair("willy", "fiona")] == pytest.approx(0.5, abs=1e-9)
    # Offspring sharing one founder parent are half-siblings (0.25).
    assert mat[_pair("vader", "xerces")] == pytest.approx(0.25, abs=1e-9)


def test_sibling_sets_correct(roster) -> None:
    """Sibling derivation: same (sire,dam), founders excluded; sibling sets match."""
    sets = full_sibling_sets(roster)
    by = {frozenset(s) for s in sets}
    # M70 full-sib groups (uno is zeek x abigail, same as abby/amber)
    assert frozenset({"abby", "amber", "uno"}) in by  # zeek x abigail
    assert frozenset({"betty", "kiki", "lily", "maxine", "zack"}) in by  # zeek x betsy
    # TAMUK iris+jade (xander x harmony)
    assert frozenset({"iris", "jade"}) in by
    # Unrelated founders must NOT be grouped: willy/isabelle/yaz have null parents
    assert frozenset({"willy", "isabelle"}) not in by
    assert frozenset({"willy", "yaz"}) not in by
    assert frozenset({"isabelle", "willy", "yaz", "ginseng", "harmony"}) not in by


def test_tiers(roster, kinship) -> None:
    """Tier mapping respects outcross_r_max and the 0.5 boundary."""
    assert tier_for_r(0.0, kinship) == PairTier.OUTCROSS
    assert tier_for_r(kinship.outcross_r_max, kinship) == PairTier.OUTCROSS
    assert tier_for_r(0.3, kinship) == PairTier.LINE_BRED
    assert tier_for_r(0.5, kinship) == PairTier.SIBLING


def test_tier_for_pair_relationship_aware(roster, kinship) -> None:
    """Operator ruling: parent-offspring and founder-sisters are line-bred (1),
    only true same-gen full-sibs are 'sibling' (5). Distinguishes what r-only
    tiering conflates at r=0.5."""
    # parent-offspring (r=0.5) -> LINE_BRED, NOT sibling.
    assert tier_for_pair("zeek", "abby", roster, 0.5, kinship) == PairTier.LINE_BRED
    assert tier_for_pair("betsy", "lily", roster, 0.5, kinship) == PairTier.LINE_BRED
    assert tier_for_pair("isabelle", "vader", roster, 0.5, kinship) == PairTier.LINE_BRED
    # founder-sister (r=0.5 via S) -> LINE_BRED, NOT sibling.
    assert tier_for_pair("abigail", "betsy", roster, 0.5, kinship) == PairTier.LINE_BRED
    assert tier_for_pair("ginseng", "harmony", roster, 0.5, kinship) == PairTier.LINE_BRED
    # true full-sib (same sire+dam) -> SIBLING.
    assert tier_for_pair("abby", "amber", roster, 0.5, kinship) == PairTier.SIBLING
    assert tier_for_pair("betty", "kiki", roster, 0.5, kinship) == PairTier.SIBLING
    assert tier_for_pair("iris", "jade", roster, 0.5, kinship) == PairTier.SIBLING
    # ordinary r-driven fallback still works for non-close pairs.
    assert tier_for_pair("yaz", "betty", roster, 0.0, kinship) == PairTier.OUTCROSS
    assert tier_for_pair("abby", "betty", roster, 0.375, kinship) == PairTier.LINE_BRED


def test_relationship_kind(roster) -> None:
    """relationship_kind correctly classifies the real pedigree pairs."""
    assert relationship_kind("zeek", "abby", roster) == "parent_offspring"
    assert relationship_kind("abby", "amber", roster) == "full_sib"
    assert relationship_kind("abigail", "betsy", roster) == "founder_sister"
    assert relationship_kind("ginseng", "harmony", roster) == "founder_sister"
    assert relationship_kind("yaz", "betty", roster) == "other"
