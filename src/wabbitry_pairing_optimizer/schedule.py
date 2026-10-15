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

__all__ = ["build_schedule", "schedule_days"]


def build_schedule(
    pairings: list[Pairing],
    max_bucks_per_day: int,
) -> dict[int, list[Pairing]]:
    """Build the day-by-day breeding calendar.

    Who gets bred on which day, given a max number of bucks that can breed on a
    single day. Model (design §8 comp 5, operator rules):

    - a buck breeds at most one doe per day;
    - at most ``max_bucks_per_day`` distinct bucks breed on any one day
      (0 / negative = unlimited: every buck with does remaining breeds each day);

    No rest days: a buck with several does simply breeds one per consecutive
    day. Assignment is deterministic: bucks are taken in sorted-name order each
    day, selecting the first eligible (still-has-does) ``max_bucks_per_day``.

    Args:
        pairings: All pairings for the round.
        max_bucks_per_day: Max distinct bucks that can breed in a single day.

    Returns:
        Mapping ``day -> [Pairing, ...]`` for days 1..round length. Day start
        at 1; empty iff ``pairings`` is empty.
    """
    if not pairings:
        return {}
    by_buck: dict[str, list[Pairing]] = {}
    for p in pairings:
        by_buck.setdefault(p.sire, []).append(p)
    # Deterministic buck + doe ordering.
    remaining = {b: sorted(ps, key=lambda x: x.dam) for b, ps in by_buck.items()}
    unlimited = max_bucks_per_day <= 0
    schedule: dict[int, list[Pairing]] = {}
    day = 1
    while remaining:
        eligible = [b for b in sorted(remaining) if remaining[b]]
        chosen = eligible if unlimited else eligible[:max_bucks_per_day]
        if chosen:
            today: list[Pairing] = []
            for b in chosen:
                today.append(remaining[b].pop(0))
                if not remaining[b]:
                    del remaining[b]
            schedule[day] = today
        day += 1
    return schedule


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
