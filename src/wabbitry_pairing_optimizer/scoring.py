"""Two-tier scoring (design §8, Phase 3).

Connects the Phase 1 kinship (r) and Phase 2 doe-productivity into the two
scores the solver optimizes:

**Tier 1 — per-pairing** (pick the best buck for one doe), HIGHER is better:
``score = -weight_r·r + weight_doe_history·productivity - tier_penalty``

Low inbreeding (r), a productive doe, and a cheap tier (outcross=0) all raise
the score. ``score_r`` is the negated r term so "minimize inbreeding" reads as
a higher score; ``tier_penalty`` is subtracted (sibling=5 cheapest to have in
the sense of lowest score).

**Tier 2 — full-solution** (rank complete assignment sets), HIGHER is better:
the six weighted components from design §8 / ADR 0004:
- sum_r          = -weight_sum_r * Σr            (minimize inbreeding)
- sum_history    = +weight_sum_history * Σprod  (reward breeding productive does)
- unbred_penalty = weight_unbred * n_unbred       (strong penalty, weight < 0)
- sibling_penalty= weight_sibling * n_sibling     (penalty per forced full-sib)
- schedule_penalty= weight_schedule_length * days (operator labor, weight < 0)
- pairability    = +weight_pairability * count    (maximize mixed-pair proxy)

``final`` = sum of the weighted components. Both tiers are HIGHER-is-better and
carried (audited) in the output so the ranking is reproducible & attributable.

Single concern: scoring (pure; inputs already computed by kinship/productivity).
"""

from __future__ import annotations

from wabbitry_pairing_optimizer.config import ScoringConfig, TierPenaltyConfig
from wabbitry_pairing_optimizer.models import Pairing, SolutionScore

__all__ = ["per_pairing_score", "full_solution_score"]


def per_pairing_score(
    sire: str,
    dam: str,
    r: float,
    productivity: float,
    pair_type: str,
    cfg: ScoringConfig,
    fixed: bool = False,
) -> Pairing:
    """Compute the per-pairing score for one (buck, doe) assignment.

    Args:
        sire: Buck name.
        dam: Doe name.
        r: Coefficient of relationship (0.0-0.5 for distinct rabbits).
        productivity: Doe productivity index (Phase 2).
        pair_type: Tier label ("outcross" | "line_bred" | "sibling").
        cfg: Scoring config (per_pairing + tier_penalty weights).
        fixed: Whether this is a pre-decided operator pair.

    Returns:
        A fully-scored ``Pairing``. Higher ``final_score`` is better.
    """
    pp = cfg.per_pairing
    tier = cfg.tier_penalty
    penalty = _tier_penalty(pair_type, tier)

    score_r = -pp.weight_r * r
    score_doe_history = pp.weight_doe_history * productivity
    final_score = score_r + score_doe_history - penalty

    return Pairing(
        sire=sire,
        dam=dam,
        pair_type=pair_type,
        kinship_r=r,
        tier_penalty=penalty,
        score_r=score_r,
        score_doe_history=score_doe_history,
        final_score=final_score,
        fixed=fixed,
    )


def _tier_penalty(pair_type: str, tier: TierPenaltyConfig) -> float:
    """The config penalty for a tier (outcross=0, line_bred=1, sibling=5)."""
    return {
        "outcross": tier.penalty_outcross,
        "line_bred": tier.penalty_line_bred,
        "sibling": tier.penalty_sibling,
    }.get(pair_type, tier.penalty_line_bred)


def full_solution_score(
    pairings: list[Pairing],
    productivity_map: dict[str, float],
    unbred_does: list[str],
    schedule_days: int,
    pairability_count: int,
    cfg: ScoringConfig,
) -> SolutionScore:
    """Compute the full-solution score for a complete assignment set.

    Args:
        pairings: All pairings (incl. fixed operator pairs).
        productivity_map: doe name -> productivity index (for the sum-history term).
        unbred_does: Does left without a buck.
        schedule_days: Estimated round length in days.
        pairability_count: Mixed-pair availability count.
        cfg: Scoring config (full_solution weights).

    Returns:
        The six-component ``SolutionScore`` (higher final is better).
    """
    fs = cfg.full_solution
    total_r = sum(p.kinship_r for p in pairings)
    total_prod = sum(productivity_map.get(p.dam, 0.0) for p in pairings)
    n_sibling = sum(1 for p in pairings if p.pair_type == "sibling")

    sum_r = -fs.weight_sum_r * total_r
    sum_history = fs.weight_sum_history * total_prod
    unbred_penalty = fs.weight_unbred * len(unbred_does)
    sibling_penalty = fs.weight_sibling * n_sibling
    schedule_penalty = fs.weight_schedule_length * schedule_days
    pairability = fs.weight_pairability * pairability_count

    final = sum_r + sum_history + unbred_penalty + sibling_penalty + schedule_penalty + pairability
    return SolutionScore(
        sum_r=sum_r,
        sum_history=sum_history,
        unbred_penalty=unbred_penalty,
        sibling_penalty=sibling_penalty,
        schedule_penalty=schedule_penalty,
        pairability=pairability,
        final=final,
    )
