"""Recipe vectors: validate stored ancestor-percentage recipes (design §2).

Each rabbit's ``recipe`` is an ancestor-percentage vector summing to 1.0. For
rabbits WITH parentage, the stored recipe must equal the half-parent recursion:
``recipe(child) = 0.5·recipe(sire) + 0.5·recipe(dam)`` (founders terminate the
walk as their own root, like a self-signed root CA). This module re-derives the
expected recipe from the pedigree and compares it against the stored one,
flagging any drift.

Note: recipes are the SOURCE OF TRUTH. Missing/culled parents are tolerated
(their contribution is treated as already folded into the child's stored recipe
when parentage is incomplete); the check only applies where parentage is
complete enough to re-derive. Single concern: recipe validation.
"""

from __future__ import annotations

from collections import defaultdict

from wabbitry_pairing_optimizer.models import Breeder

__all__ = ["RecipeError", "verify_recipes"]


class RecipeError(Exception):
    """Raised when a rabbit's stored recipe disagrees with the pedigree-derived value."""


def verify_recipes(breeders: list[Breeder], tolerance: float = 1e-6) -> list[str]:
    """Re-derive each rabbit's recipe from parentage and compare to its stored one.

    Args:
        breeders: The validated roster.
        tolerance: Max acceptable per-ancestor / total drift.

    Returns:
        List of rabbit names whose stored recipe drifts beyond ``tolerance``.

    Raises:
        RecipeError: If a rabbit has exactly one parent (half-derived) yet a
            full recipe that implies two, or other such structurally-broken
            parentage (this is a data bug, not a drift).
    """
    by_name = {b.name: b for b in breeders}

    def _derive(name: str) -> dict[str, float]:
        """Derive the ancestor-percentage recipe for ``name`` via half-parents."""
        if by_name[name].sire is None and by_name[name].dam is None:
            # Founder / root: self is the entire recipe.
            return {name: 1.0}
        if (by_name[name].sire is None) != (by_name[name].dam is None):
            raise RecipeError(f"{name!r} has only one recorded parent")
        acc: defaultdict[str, float] = defaultdict(float)
        for parent in (by_name[name].sire, by_name[name].dam):
            if parent is None:
                continue
            for anc, frac in _derive(parent).items():
                acc[anc] += 0.5 * frac
        return dict(acc)

    drifters: list[str] = []
    for b in breeders:
        if b.sire is None and b.dam is None:
            expected = {b.name: 1.0}
        else:
            expected = _derive(b.name)
        stored = b.recipe
        keys = set(expected) | set(stored)
        diff = sum(abs(expected.get(k, 0.0) - stored.get(k, 0.0)) for k in keys)
        if diff > tolerance:
            drifters.append(b.name)
    return drifters
