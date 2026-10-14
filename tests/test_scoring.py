"""Phase 3 tests: two-tier scoring (design §8, ADR 0004)."""

from __future__ import annotations

from pathlib import Path

import pytest

from wabbitry_pairing_optimizer.config import load_config
from wabbitry_pairing_optimizer.models import Pairing
from wabbitry_pairing_optimizer.scoring import full_solution_score, per_pairing_score

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA = REPO_ROOT / "data"


@pytest.fixture(scope="module")
def scoring_cfg():
    return load_config(DATA / "config.toml").scoring


def test_per_pairing_outcross_beats_sibling(scoring_cfg) -> None:
    """Low-r outcross scores higher than a high-r sibling for the same doe.
    A lower kinship r must raise the per-pairing score (minimize inbreeding).
    """
    same_doe_prod = 3.0
    sib = per_pairing_score("zeekb", "doe", 0.5, same_doe_prod, "sibling", scoring_cfg)
    out = per_pairing_score("zeekb", "doe", 0.0, same_doe_prod, "outcross", scoring_cfg)
    assert out.final_score > sib.final_score
    assert sib.pair_type == "sibling"
    assert out.pair_type == "outcross"


def test_per_pairing_productive_doe_scores_higher(scoring_cfg) -> None:
    """For the same r/tier, a more productive doe scores higher."""
    low = per_pairing_score("buck", "dlo", 0.1, 2.0, "line_bred", scoring_cfg)
    high = per_pairing_score("buck", "dhi", 0.1, 5.0, "line_bred", scoring_cfg)
    assert high.final_score > low.final_score


def test_per_pairing_exact_formula(scoring_cfg) -> None:
    """score = -wr*r + wh*prod - penalty(0 for outcross)."""
    pp = per_pairing_score("buck", "doe", 0.1, 4.0, "outcross", scoring_cfg)
    wr = scoring_cfg.per_pairing.weight_r
    wh = scoring_cfg.per_pairing.weight_doe_history
    pen = scoring_cfg.tier_penalty.penalty_outcross
    expected = -wr * 0.1 + wh * 4.0 - pen
    assert pp.final_score == pytest.approx(expected, abs=1e-9)
    assert pp.score_r == pytest.approx(-wr * 0.1, abs=1e-9)
    assert pp.score_doe_history == pytest.approx(wh * 4.0, abs=1e-9)
    assert pp.tier_penalty == pen


def test_sibling_penalty_weighted(scoring_cfg) -> None:
    """Sibling tier carries the full penalty (default 5) into the final score."""
    s = per_pairing_score("b", "d", 0.5, 1.0, "sibling", scoring_cfg)
    assert s.tier_penalty == scoring_cfg.tier_penalty.penalty_sibling
    # The penalty is subtracted from final_score: pins that a dropped tier
    # penalty (a common bug) shows up here.
    pen = scoring_cfg.tier_penalty.penalty_sibling
    wr = scoring_cfg.per_pairing.weight_r
    wh = scoring_cfg.per_pairing.weight_doe_history
    assert s.final_score == pytest.approx(-wr * 0.5 + wh * 1.0 - pen, abs=1e-9)


def test_full_solution_unbred_discounts(scoring_cfg) -> None:
    """Leaving a doe unbred strongly lowers the full-solution score."""
    pairs = [
        Pairing(
            sire="s1",
            dam="d1",
            pair_type="outcross",
            kinship_r=0.0,
            tier_penalty=0.0,
            score_r=0.0,
            score_doe_history=1.0,
            final_score=1.0,
        )
    ]
    prod = {"d1": 4.0}
    good = full_solution_score(pairs, prod, [], 1, 0, scoring_cfg)
    bad = full_solution_score(pairs, prod, ["d2"], 1, 0, scoring_cfg)
    assert good.final > bad.final
    # unbred penalty = weight_unbred * n (negative for n>0)
    assert bad.unbred_penalty == pytest.approx(
        scoring_cfg.full_solution.weight_unbred * 1, abs=1e-9
    )
    assert bad.unbred_penalty < 0


def test_full_solution_sums_components(scoring_cfg) -> None:
    """final == sum of the six weighted components."""
    pairs = [
        Pairing(
            sire="s1",
            dam="d1",
            pair_type="outcross",
            kinship_r=0.0,
            tier_penalty=0.0,
            score_r=0.0,
            score_doe_history=1.0,
            final_score=1.0,
        ),
        Pairing(
            sire="s2",
            dam="d2",
            pair_type="sibling",
            kinship_r=0.5,
            tier_penalty=5.0,
            score_r=-0.5,
            score_doe_history=1.0,
            final_score=-4.5,
        ),
    ]
    prod = {"d1": 4.0, "d2": 3.0}
    sc = full_solution_score(pairs, prod, ["d3"], 2, 3, scoring_cfg)
    total = (
        sc.sum_r
        + sc.sum_history
        + sc.unbred_penalty
        + sc.sibling_penalty
        + sc.schedule_penalty
        + sc.pairability
    )
    assert sc.final == pytest.approx(total, abs=1e-9)
    # sum_r is negated (minimize inbreeding): total r = 0.5 -> suma = -0.5*wr
    assert sc.sum_r == pytest.approx(-scoring_cfg.full_solution.weight_sum_r * 0.5, abs=1e-9)
    # sibling penalty applies (one sibling pair)
    assert sc.sibling_penalty == pytest.approx(
        scoring_cfg.full_solution.weight_sibling * 1, abs=1e-9
    )


def test_full_solution_higher_pairability_preferred(scoring_cfg) -> None:
    """More mixed pairs raise the full-solution score."""
    pairs = [
        Pairing(
            sire="s1",
            dam="d1",
            pair_type="outcross",
            kinship_r=0.0,
            tier_penalty=0.0,
            score_r=0.0,
            score_doe_history=1.0,
            final_score=1.0,
        )
    ]
    prod = {"d1": 4.0}
    low = full_solution_score(pairs, prod, [], 1, 2, scoring_cfg)
    high = full_solution_score(pairs, prod, [], 1, 8, scoring_cfg)
    assert high.final > low.final
