"""Doe productivity index (design §8, Phase 2).

Ranks how reliable a doe's litters are for scoring and breeding decisions:

``own_score = size_weight * trimmed_avg_size + consistency_weight * consistency``

- ``trimmed_avg_size``: mean litter size after outlier trimming (IQR or Z-score
  per config; ``outlier_trim`` off disables trimming).
- ``consistency``: ``1 / (1 + variance)`` — bounded (0,1], higher when the
  doe's litter sizes cluster tightly.

Thin own-history folds toward the mother by evidence:

``w_own = own_n / (own_n + K)``; ``index = w_own*own_score + (1-w_own)*mother_index``

where ``mother_index`` is the mother's own score (computed from the mother's own
litters; founders terminate). If the mother has no history (unknown or a buck),
the index is just the doe's own score. A doe with no litters whose dam has
history inherits the dam's index (w_own=0).

Note on thin records: a single own litter scores full consistency
(``1/(1+0)`` = 1.0), so a thin-record doe can rank high on one big litter (e.g.
fiona). That is the recorded reality by design; if the operator prefers to
discount it, adjust ``consistency_weight`` or handle thin-records explicitly.

Single concern: the productivity index (pure, no I/O; takes litters + roster).
"""

from __future__ import annotations

import math
from collections import defaultdict

from wabbitry_pairing_optimizer.config import ProductivityConfig
from wabbitry_pairing_optimizer.load_litters import Litter
from wabbitry_pairing_optimizer.models import Breeder

__all__ = ["productivity_index", "doe_production_scores"]


def _trimmed_mean(sizes: list[float], cfg: ProductivityConfig) -> float:
    """Mean of ``sizes`` with outliers removed per config.

    IQR: drop values beyond ``[q1 - t*IQR, q3 + t*IQR]`` (default t=1.5).
    Z-score: drop values beyond ``t`` sample standard deviations.
    "none" or ``outlier_trim=False``: no trimming.
    """
    if not sizes:
        return 0.0
    if not cfg.outlier_trim or cfg.outlier_method == "none":
        return sum(sizes) / len(sizes)
    if len(sizes) < 4:  # too few to estimate IQR/std reliably
        return sum(sizes) / len(sizes)

    s = sorted(sizes)
    if cfg.outlier_method == "zscore":
        mean = sum(s) / len(s)
        var = sum((x - mean) ** 2 for x in s) / max(len(s) - 1, 1)
        sd = math.sqrt(var)
        if sd == 0:
            return mean
        kept = [x for x in s if abs(x - mean) <= cfg.outlier_threshold * sd]
        return sum(kept) / len(kept) if kept else mean

    # default IQR
    q1 = s[len(s) // 4]
    q3 = s[(3 * len(s)) // 4]
    iqr = q3 - q1
    if iqr == 0:
        return sum(s) / len(s)
    lo, hi = q1 - cfg.outlier_threshold * iqr, q3 + cfg.outlier_threshold * iqr
    kept = [x for x in s if lo <= x <= hi]
    return sum(kept) / len(kept) if kept else sum(s) / len(s)


def _own_score(sizes: list[float], cfg: ProductivityConfig) -> float:
    """Blend of trimmed-avg size and consistency for a set of own litters."""
    if not sizes:
        return 0.0
    mean = _trimmed_mean(sizes, cfg)
    var = sum((x - mean) ** 2 for x in sizes) / max(len(sizes) - 1, 1)
    consistency = 1.0 / (1.0 + var)
    return cfg.size_weight * mean + cfg.consistency_weight * consistency


def productivity_index(
    doe: Breeder, litters: list[Litter], roster: list[Breeder], cfg: ProductivityConfig
) -> float:
    """The productivity index for a doe, blending her own record with her dam's.

    Args:
        doe: The doe to score (any rabbit with a dam link; usually a doe).
        litters: All litter records (used to gather the doe's and dam's own litters).
        roster: Full roster (to look up the dam by name).
        cfg: Productivity config.

    Returns:
        The productivity index (>= 0). Higher = more reliable producer.
    """
    by_dam: defaultdict[str, list[Litter]] = defaultdict(list)
    for lit in litters:
        by_dam[lit.dam].append(lit)

    own_sizes = [float(lit.size) for lit in by_dam.get(doe.name, [])]
    own_n = len(own_sizes)
    own_score = _own_score(own_sizes, cfg)

    # Determine the dam's index (mother's own score) if she has any history.
    mother_index: float | None = None
    if doe.dam is not None:
        mother_sizes = [float(lit.size) for lit in by_dam.get(doe.dam, [])]
        if mother_sizes:  # mother has production history
            mother_index = _own_score(mother_sizes, cfg)

    if mother_index is None:
        return own_score

    w_own = own_n / (own_n + cfg.evidence_k)
    return w_own * own_score + (1.0 - w_own) * mother_index


def doe_production_scores(
    breeders: list[Breeder], litters: list[Litter], cfg: ProductivityConfig
) -> dict[str, float]:
    """Productivity index for every active doe (design §8, sum-history input).

    Args:
        breeders: Full roster.
        litters: All litter records.
        cfg: Productivity config.

    Returns:
        Mapping doe name -> productivity index for active, non-Composite does.
    """
    result: dict[str, float] = {}
    for b in breeders:
        if not b.culled and not b.is_composite and b.gender == "F":
            result[b.name] = productivity_index(b, litters, breeders, cfg)
    return result
