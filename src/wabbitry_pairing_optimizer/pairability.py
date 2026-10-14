"""Pairability metric: how many mixed pairs a round's litters support (design §4).

SWAPPABLE SEAM: the current "availability" mode is the cheap <b>mixed-pair
availability count</b> under the uniform 50/50-litter assumption:

``min(M70 doe-kits, TAMUK buck-kits) + min(TAMUK doe-kits, M70 buck-kits)``

A mixed pair = 1 doe from one strain's litter + 1 buck from the OTHER strain's
litter (cross-strain, so automatically unrelated — pool separation, r≈0). This
is the monotone building block the separate trio optimizer extends into full
mixed trios (buck + 2 sister-does).

Counting in litter-units: each bred doe produces one litter, split 50/50 so it
yields 0.5 doe-kits + 0.5 buck-kits of her strain. The count is DETERMINISTIC
from the pairings alone (forward-looking, per design §4).

Note: because every active doe is always bred (design rule 4), the strain-level
litter counts are CONSTANT across feasible solutions, so this count does NOT
differentiate solutions — it matters only when the exact trio optimizer runs
once on the winner (report phase). Kept faithful as the swappable seam.

Single concern: pairability of a solution (pure).
"""

from __future__ import annotations

from wabbitry_pairing_optimizer.models import Breeder, Solution

__all__ = ["pairability"]

#: strain token of the two closed breeding pools.
STRAIN_M70 = "M70"
STRAIN_TAMUK = "TAMUK"


def pairability(solution: Solution, roster: list[Breeder], mode: str = "availability") -> float:
    """Mixed-pair availability count for a solution (litter-units).

    Args:
        solution: The completed solution (pairings + unbred does).
        roster: Full roster (to resolve each dam's / sire's strain).
        mode: Metric mode (config `[pairability].mode`). Only "availability"
            is implemented; other modes raise.

    Returns:
        The mixed-pair availability count (non-negative). Constant across
        solutions that breed all does, so it does not discriminate here.
    """
    if mode != "availability":
        raise NotImplementedError(f"pairability mode {mode!r} not implemented")

    by = {b.name: b for b in roster}

    def strain(name: str) -> str:
        return by[name].strain

    m70_does = sum(1 for p in solution.pairings if strain(p.dam) == STRAIN_M70)
    tamuk_does = sum(1 for p in solution.pairings if strain(p.dam) == STRAIN_TAMUK)

    # Each litter yields 0.5 doe-kits + 0.5 buck-kits of its strain (50/50).
    m70_doe_units = 0.5 * m70_does
    m70_buck_units = 0.5 * m70_does
    tamuk_doe_units = 0.5 * tamuk_does
    tamuk_buck_units = 0.5 * tamuk_does

    return min(m70_doe_units, tamuk_buck_units) + min(tamuk_doe_units, m70_buck_units)
