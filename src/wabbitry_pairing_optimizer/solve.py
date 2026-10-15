"""Assignment solver: multi-start ranked greedy (design §6, Phase 4).

Produces a complete breeding round from the Phase 1/2/3 building blocks:

1. Fixed operator pairs (e.g. Yaz -> betty/lily/kiki) are applied first: their
   full rationale scores are computed (uniform with auto pairs), and both sides
   are excluded from the automatic assignment pools.
2. Multi-start ranked greedy per strain pool (M70 / TAMUK independent): each
   run shuffles the remaining does and bucks, iterates does, and assigns each
   the highest-scoring buck by the per-pairing score (r + doe_history; ties
   resolve to shuffled order). Buck load is allowed (a buck may service
   multiple does — design rule 5); the ``[diversity]`` policy (hard cap +
   soft load penalty) makes buck-spread reachable during GENERATION so the
   multi-start search can propose diverse assignments. Full-sib is naturally
   a last resort via the heavy sibling penalty.
3. Each complete solution scores via the full-solution objective (Phase 3).
   Stall-based termination: stop only after MIN_RUNS and when no new winner
   has appeared in STALL_LIMIT consecutive runs. Keep the single best.
4. The winner is returned as a ``Solution`` with schedule + pairability.

Single concern: solving (pure; all inputs already computed).
"""

from __future__ import annotations

import random

from wabbitry_pairing_optimizer.config import Config
from wabbitry_pairing_optimizer.kinship import coancestry_matrix_r, tier_for_pair
from wabbitry_pairing_optimizer.load_litters import Litter
from wabbitry_pairing_optimizer.models import Breeder, Pairing, Solution
from wabbitry_pairing_optimizer.pairability import pairability
from wabbitry_pairing_optimizer.productivity import doe_production_scores
from wabbitry_pairing_optimizer.schedule import schedule_days
from wabbitry_pairing_optimizer.scoring import full_solution_score, per_pairing_score

__all__ = ["solve"]

#: kinship matrix keyed by canonical (sorted) pair -> r.
RMatrix = dict[tuple[str, str], float]
#: doe name -> productivity index.
ProdMap = dict[str, float]


def solve(
    roster: list[Breeder],
    litters: list[Litter],
    config: Config,
    fixed_pairs: list[tuple[str, str]] | None = None,
) -> Solution:
    """Solve one breeding round (multi-start ranked greedy).

    Args:
        roster: Full roster (breeders).
        litters: All litter records (for productivity).
        config: Full typed config (kinship/productivity/scoring/optimization).
        fixed_pairs: Optional list of (sire, dam) operator pre-decided pairs.

    Returns:
        The winning ``Solution`` (all pairings, full-solution score, schedule,
        pairability).
    """
    fixed_pairs = fixed_pairs or []
    mat = coancestry_matrix_r(roster, config.kinship)
    prod = doe_production_scores(roster, litters, config.productivity)
    by = {b.name: b for b in roster}

    opt = config.optimization
    rng = random.Random(opt.seed if opt.seed else None)  # noqa: S311 - intentional seeded non-crypto PRNG for reproducible shuffle

    # Active does/bucks per strain (pools independent per design §6).
    strains: dict[str, tuple[list[str], list[str]]] = {}
    for b in roster:
        if not b.culled and not b.is_composite:
            does_l, bucks_l = strains.setdefault(b.strain, ([], []))
            target = does_l if b.gender == "F" else bucks_l
            target.append(b.name)

    all_pairings: list[Pairing] = []
    for strain, (strain_does, strain_bucks) in strains.items():
        does_left = set(strain_does)
        used_bucks: set[str] = set()

        # Fixed pairs first: score them, exclude both sides from auto pools.
        for sire, dam in fixed_pairs:
            if by[dam].strain != strain:
                continue
            rv = mat[(sire, dam) if sire < dam else (dam, sire)]
            tier = tier_for_pair(sire, dam, roster, rv, config.kinship)
            all_pairings.append(
                per_pairing_score(
                    sire, dam, rv, prod.get(dam, 0.0), tier, config.scoring, fixed=True
                )
            )
            used_bucks.add(sire)
            does_left.discard(dam)

        if not does_left:
            continue

        auto_bucks = [b for b in strain_bucks if b not in used_bucks]
        best_pairs = _multi_start(does_left, auto_bucks, mat, prod, roster, config, rng)
        all_pairings.extend(best_pairs)

    return _assemble(all_pairings, roster, config, prod)


def _assign_one(
    dam: str,
    bucks: list[str],
    mat: RMatrix,
    prod: ProdMap,
    roster: list[Breeder],
    config: Config,
    load: dict[str, int] | None = None,
) -> Pairing | None:
    """Pick the best-scoring buck for one doe under a buck-load policy.

    Applies the diversity policy to AUTO assignment only (fixed pairs are
    excluded from auto pools upstream). A buck at the hard ``max_does_per_buck``
    cap is removed from candidacy; otherwise each buck's effective score drops
    by ``config.diversity.load_penalty`` per doe it already holds in the
    current run, so the greedy can spread but still concentrate when a buck is
    the only good match. Ties resolve to first in list order.

    Returns ``None`` when every candidate buck is at its hard cap (a tight-pool
    failure the caller lets the full-solution unbred penalty rank low); the
    caller never asserts — an unassigned doe is a lower-ranked solution, not a
    hard error.

    Args:
        dam: Doe being assigned.
        bucks: Candidate buck list (shuffled by the caller).
        mat: Kinship r matrix.
        prod: Doe productivity map.
        roster: Full validated roster.
        config: Full typed config (read ``diversity``).
        load: Current per-buck doe counts in this run (mutable, updated by the
            caller after assignment).

    Returns:
        The chosen ``Pairing``, or ``None`` if every buck is at the hard cap.
    """
    load = load or {}
    cap = config.diversity.max_does_per_buck
    penalty = config.diversity.load_penalty
    best: Pairing | None = None
    best_scaled: float | None = None
    for sire in bucks:
        if cap and load.get(sire, 0) >= cap:
            continue
        rv = mat[(sire, dam) if sire < dam else (dam, sire)]
        tier = tier_for_pair(sire, dam, roster, rv, config.kinship)
        p = per_pairing_score(sire, dam, rv, prod.get(dam, 0.0), tier, config.scoring)
        scaled = p.final_score - penalty * load.get(sire, 0)
        if best_scaled is None or scaled > best_scaled:
            best = p
            best_scaled = scaled
    return best


def _multi_start(
    does_left: set[str],
    auto_bucks: list[str],
    mat: RMatrix,
    prod: ProdMap,
    roster: list[Breeder],
    config: Config,
    rng: random.Random,
) -> list[Pairing]:
    """Multi-start ranked greedy with stall-based termination (design §6)."""
    opt = config.optimization
    doess = sorted(does_left)
    best_pairs: list[Pairing] | None = None
    best_final: float | None = None
    runs = 0
    since_best = 0

    while True:
        runs += 1
        order = doess[:]
        rng.shuffle(order)
        buck_order = auto_bucks[:]
        rng.shuffle(buck_order)

        pairs: list[Pairing] = []
        load: dict[str, int] = {}
        for d in order:
            p = _assign_one(d, buck_order, mat, prod, roster, config, load)
            if p is None:
                continue  # every buck at hard cap for this doe; leaves it unbred
            load[p.sire] = load.get(p.sire, 0) + 1
            pairs.append(p)

        # Full-solution score ranks the complete assignment set.
        assigned = {p.dam for p in pairs}
        unbred = [d for d in doess if d not in assigned]
        final = full_solution_score(
            [p for p in pairs if p is not None], prod, unbred, 0, 0, config.scoring
        ).final

        if best_final is None or final > best_final:
            best_final = final
            best_pairs = pairs
            since_best = 0
        else:
            since_best += 1

        if runs >= opt.min_runs and since_best >= opt.stall_limit:
            break
        if runs >= 200000:  # hard safety bound
            break

    assert best_pairs is not None, "solver produced no best solution"  # noqa: S101 - internal invariant
    return [p for p in best_pairs if p is not None]


def _assemble(
    pairings: list[Pairing],
    roster: list[Breeder],
    config: Config,
    prod: ProdMap,
) -> Solution:
    """Build the winning Solution with score, schedule, and pairability."""
    assigned = {p.dam for p in pairings}
    all_does = [b.name for b in roster if b.gender == "F" and not b.culled and not b.is_composite]
    unbred = sorted(set(all_does) - assigned)

    opt = config.optimization
    days = schedule_days(pairings, opt.buck_batch_capacity)
    pre = Solution(pairings=pairings, unbred_does=unbred, schedule_days=days)
    pc = int(pairability(pre, roster, config.pairability.mode))
    score = full_solution_score(pairings, prod, unbred, days, pc, config.scoring)

    return Solution(
        pairings=pairings, unbred_does=unbred, score=score, schedule_days=days, pairability_count=pc
    )
