"""Round schedule: calendar-length estimate (design §8 comp 5, Phase 4).

The operator does one breeding day per doe, waiting a full day between breeding
days, and manages about ``buck_batch_capacity`` bucks at once. A buck servicing
``k`` does therefore spans ``2k-1`` day buckets (k breeding days + k-1 rest
days). Bucks are batched into groups of <=``buck_batch_capacity``; a batch's
span is the max over its bucks; the round length is the SUM of batch spans
(a new batch starts only when the previous batch's longest buck is done).

Single concern: turn a set of pairings into a round-length estimate.
"""

from __future__ import annotations

from collections import Counter

from wabbitry_pairing_optimizer.models import Pairing

__all__ = ["schedule_days"]


def schedule_days(pairings: list[Pairing], buck_batch_capacity: int) -> int:
    """Estimate the round calendar length in days.

    Args:
        pairings: All pairings for the round.
        buck_batch_capacity: Max bucks operated concurrently (batching).

    Returns:
        Round length in days (>= 1 if any pairings exist, else 0).
    """
    if not pairings:
        return 0
    per_buck = Counter(p.dam for p in pairings)  # does per buck == litters per buck
    # A buck servicing k does spans 2k-1 days (k breed days + (k-1) rest days).
    buck_spans = [2 * k - 1 for k in per_buck.values()]

    # Batch bucks (arbitrary order) into groups of capacity; batch span = max.
    total = 0
    for i in range(0, len(buck_spans), buck_batch_capacity):
        batch = buck_spans[i : i + buck_batch_capacity]
        total += max(batch)
    return total
