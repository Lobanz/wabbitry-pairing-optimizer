"""Kinship: coefficient of relationship r + founder-sister factor (design §5).

Implements the standard coefficient of relationship from the pedigree, with the
configurable founder-sister factor S (ADR 0003):

- ``r(A,B) = 2 · f(A,B)`` where ``f`` is coancestry.
- Coancestry recursion over sire/dam:
    ``f(A,A) = ½·(1 + f(sA, dA))``
    ``f(A,B) = ¼·(f(sA,sB) + f(sA,dB) + f(dA,sB) + f(dA,dB))``  for A≠B
- Founders (no parents) are root boundaries: ``f(A,A)=0.5`` (so ``r=1.0``) for
  a founder with itself; **unrelated distinct founders** ``f=0``.
- **Founder-sister factor S:** two founder-sisters (``founder_sisters``) share
  unknown-parent blood; they are treated as sharing fraction S, so for sister
  founders ``r = S`` and the shared blood propagates through descendants.

Also derives **full-sibling sets** per the corrected rule (design §2): full-sib
⟺ same ``(sire, dam)`` with parentage; **null-parentage founders are EXCLUDED**
from that grouping (only ``founder_sisters`` marks founder sibs), so unrelated
founders (e.g. willy / isabelle / yaz) are never falsely grouped.

Single concern: kinship + sibling derivation (pure, no I/O).
"""

from __future__ import annotations

from wabbitry_pairing_optimizer.config import KinshipConfig
from wabbitry_pairing_optimizer.models import Breeder

__all__ = [
    "PairTier",
    "RelationshipKind",
    "relationship_kind",
    "tier_for_pair",
    "tier_for_r",
    "coancestry_matrix_r",
    "full_sibling_sets",
]


class PairTier:
    """Kinship tier labels (design §5)."""

    OUTCROSS = "outcross"
    LINE_BRED = "line_bred"
    SIBLING = "sibling"


class RelationshipKind:
    """Relationship kind between two rabbits (relationship-aware tiering)."""

    PARENT_OFFSPRING = "parent_offspring"
    FULL_SIB = "full_sib"
    FOUNDER_SISTER = "founder_sister"
    OTHER = "other"


def relationship_kind(a: str, b: str, breeders: list[Breeder]) -> str:
    """Classify the biological relationship between two rabbits.

    Distinguishes the cases the r-only tier conflates (design §3 rule 8, §5):
    - ``parent_offspring``: one is the other's recorded sire or dam.
    - ``full_sib``: same (sire, dam), both parents known (same generation).
    - ``founder_sister``: each listed in the other's ``founder_sisters``.
    - ``other``: everything else (cousins, half-sibs, unrelated...).

    Args:
        a: First rabbit name.
        b: Second rabbit name.
        breeders: Full roster (for parentage + founder_sisters lookup).

    Returns:
        One of the ``RelationshipKind`` constants.
    """
    by = {x.name: x for x in breeders}
    ra, rb = by[a], by[b]
    if ra.sire == b or ra.dam == b or rb.sire == a or rb.dam == a:
        return RelationshipKind.PARENT_OFFSPRING
    if ra.sire and ra.dam and ra.sire == rb.sire and ra.dam == rb.dam:
        return RelationshipKind.FULL_SIB
    if a in set(rb.founder_sisters) or b in set(ra.founder_sisters):
        return RelationshipKind.FOUNDER_SISTER
    return RelationshipKind.OTHER


def tier_for_pair(a: str, b: str, breeders: list[Breeder], r: float, cfg: KinshipConfig) -> str:
    """Relationship-aware tier for a pair (supersedes r-only tiering).

    Per operator ruling (2026-10-15): parent-offspring and founder-sisters are
    NORMAL, allowed line-breeding (penalty 1), NOT last-resort like true
    same-generation full-sibs (penalty 5). Only a true full-sib forces the
    "sibling" tier; everything else falls through to r-driven tiering.
    """
    kind = relationship_kind(a, b, breeders)
    if kind == RelationshipKind.FULL_SIB:
        return PairTier.SIBLING
    if kind in (RelationshipKind.PARENT_OFFSPRING, RelationshipKind.FOUNDER_SISTER):
        return PairTier.LINE_BRED
    return tier_for_r(r, cfg)


def tier_for_r(r: float, cfg: KinshipConfig) -> str:
    """Map a kinship r to its tier (design §5 thresholds).

    Args:
        r: Coefficient of relationship.
        cfg: Kinship config (outcross_r_max).

    Returns:
        "outcross" (r <= outcross_r_max), "line_bred" (< ~0.5), "sibling" (>= ~0.5).
    """
    if r <= cfg.outcross_r_max:
        return PairTier.OUTCROSS
    if r < 0.5:
        return PairTier.LINE_BRED
    return PairTier.SIBLING


def coancestry_matrix_r(
    breeders: list[Breeder], cfg: KinshipConfig
) -> dict[tuple[str, str], float]:
    """Compute r(A,B) for every (unordered) pair of distinct rabbits.

    Args:
        breeders: Validated roster.
        cfg: Kinship config (founder-sister factor S).

    Returns:
        Mapping ``(nameA, nameB) -> r`` with nameA < nameB lexicographically,
        containing every distinct-rabbit pair (r is symmetric, diagonal implied 1.0).
    """
    by_name = {b.name: b for b in breeders}
    sister_sets: dict[str, set[str]] = {}
    for b in breeders:
        sister_sets[b.name] = set(b.founder_sisters)

    def f(a: str | None, b: str | None) -> float:
        """Coancestry between two rabbit identities (None => unrelated)."""
        if a is None or b is None:
            return 0.0
        if a == b:
            ra = by_name[a]
            return 0.5 * (1.0 + f(ra.sire, ra.dam))
        ra, rb = by_name[a], by_name[b]
        # both founders: siblings?  else unrelated
        if ra.sire is None and ra.dam is None and rb.sire is None and rb.dam is None:
            if a in sister_sets.get(b, set()) or b in sister_sets.get(a, set()):
                return cfg.sister_factor / 2.0
            return 0.0
        if ra.sire is None and ra.dam is None:
            # a is a founder, b has parents: a random allele of b comes from each
            # parent with prob 1/2, so f(a,b) = avg over the two parents.
            return 0.5 * (f(a, rb.sire) + f(a, rb.dam))
        if rb.sire is None and rb.dam is None:
            return 0.5 * (f(ra.sire, b) + f(ra.dam, b))
        return 0.25 * (
            f(ra.sire, rb.sire) + f(ra.sire, rb.dam) + f(ra.dam, rb.sire) + f(ra.dam, rb.dam)
        )

    result: dict[tuple[str, str], float] = {}
    names = sorted(by_name)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            left, right = names[i], names[j]
            result[(left, right)] = 2.0 * f(left, right)
    return result


def full_sibling_sets(breeders: list[Breeder]) -> list[list[str]]:
    """Derive full-sibling groups per the corrected rule (design §2).

    Full-sib ⟺ same (sire, dam) **with parentage**. Rabbits with null parents
    are EXCLUDED from this grouping (only ``founder_sisters`` marks founder
    sibs, handled separately). Returns groups of >=2.

    Args:
        breeders: Validated roster.

    Returns:
        Groups of >=2 rabbits that are full siblings by parentage.
    """
    groups: dict[tuple[str, str], list[str]] = {}
    for b in breeders:
        if b.sire is not None and b.dam is not None:
            groups.setdefault((b.sire, b.dam), []).append(b.name)
    return [sorted(mem) for mem in groups.values() if len(mem) >= 2]
