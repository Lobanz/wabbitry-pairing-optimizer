"""Round schedule: day-by-day calendar + calendar-length estimate (design §8).

The operator does one breeding day per doe, and a buck never breeds two days
in a row — rest days are now IN the model (operator ruling 2026-10-24: "bucks
are bred every day, but not the same buck on consecutive days"). A buck
servicing ``k`` does therefore spans ``2k-1`` day buckets (k breeding days +
k-1 rest days). Bucks are batched into groups of <=``buck_batch_capacity``; a
batch's span is the max over its bucks; the round length is the SUM of batch
spans (a new batch starts only when the previous batch's longest buck is done).

Two concerns, one module:
- ``build_schedule`` — the day-by-day breeding CALENDAR: an alternating
  assignment found by a multi-start search (fewest round days, then fewest
  idle days), deterministic when seeded.
- ``schedule_days`` — the round-LENGTH estimate used by the solver objective
  (unchanged by the alternation ruling).
"""

from __future__ import annotations

import random
from collections import Counter

from wabbitry_pairing_optimizer.models import Pairing

__all__ = ["build_schedule", "schedule_days", "schedule_rng"]

#: Multi-start restarts for the calendar search. Deliberately a named constant,
#: NOT a config knob: the calendar is a render concern and ~200 restarts over a
#: ~13-pairing round is trivially fast. The search samples both "breed them
#: all" and "hold one back for tomorrow" choices each day.
SCHEDULE_RESTARTS = 200


def schedule_rng(seed: int) -> random.Random:
    """RNG for schedule construction, honoring the tool's seed semantics.

    Args:
        seed: Active run seed (0 = seedless/random; positive = reproducible).

    Returns:
        A ``random.Random`` — unseeded for seed 0, seeded otherwise.
    """
    # Seeded non-crypto PRNG is REQUIRED here (reproducible calendars); a crypto
    # RNG cannot be seeded, so it would break the seed contract — same rationale
    # as the solver's seeded shuffle.
    return random.Random(seed) if seed != 0 else random.Random()  # noqa: S311


def build_schedule(
    pairings: list[Pairing],
    max_bucks_per_day: int,
    rng: random.Random | None = None,
) -> dict[int, list[Pairing]]:
    """Build the day-by-day breeding calendar (alternating bucks).

    Model (design §8, operator rules 2026-10-24):

    - a buck breeds at most one doe per day;
    - a buck NEVER breeds on two consecutive days (rest-day spacing is part
      of the model — reverses the earlier "no rest days" ruling);
    - at most ``max_bucks_per_day`` distinct bucks breed on any one day
      (0 / negative = unlimited);
    - every breeding is scheduled exactly once;
    - idle days (days with no breeding) are minimized AFTER the round length.

    With ``rng`` provided, run ``SCHEDULE_RESTARTS`` greedy constructions
    (seeded shuffles + a per-day "hold one back to cover tomorrow" choice) and
    keep the best by (round days, idle days). With ``rng=None`` a single
    deterministic pass breeds every eligible buck each day — the compression
    baseline; callers that want the optimized calendar pass a seeded RNG.

    Args:
        pairings: All pairings for the round.
        max_bucks_per_day: Max distinct bucks that can breed in a single day.
        rng: Seeded ``random.Random`` for the reproducible multi-start search.

    Returns:
        Mapping ``day -> [Pairing, ...]`` for days 1..round length. Days with
        no breeding are absent — the gap in day numbers IS the rest/idle day.
    """
    if not pairings:
        return {}
    restarts = SCHEDULE_RESTARTS if rng is not None else 1
    best_sched: dict[int, list[Pairing]] | None = None
    best_key: tuple[int, int] | None = None
    for _ in range(restarts):
        sched = _schedule_pass(pairings, max_bucks_per_day, rng)
        key = _schedule_key(sched)
        if best_key is None or key < best_key:
            best_key = key
            best_sched = sched
    assert best_sched is not None  # noqa: S101 - non-empty pairings always yield a schedule
    return best_sched


def _schedule_key(sched: dict[int, list[Pairing]]) -> tuple[int, int]:
    """(round days, idle days) — lower is better; round days dominate."""
    if not sched:
        return (0, 0)
    round_days = max(sched)
    idle_days = round_days - len(sched)  # days 1..round_days with no breeding
    return (round_days, idle_days)


def _schedule_pass(
    pairings: list[Pairing],
    max_bucks_per_day: int,
    rng: random.Random | None,
) -> dict[int, list[Pairing]]:
    """One greedy calendar construction (optionally randomized)."""
    by_buck: dict[str, list[Pairing]] = {}
    for p in pairings:
        by_buck.setdefault(p.sire, []).append(p)

    buckets = sorted(by_buck)
    if rng is not None:
        rng.shuffle(buckets)
        for b in buckets:
            rng.shuffle(by_buck[b])

    remaining: dict[str, list[Pairing]] = {b: list(ps) for b, ps in by_buck.items()}
    schedule: dict[int, list[Pairing]] = {}
    day = 1
    last_bred: set[str] = set()  # bucks bred yesterday (no-consecutive rule)
    while any(remaining.values()):
        eligible = [b for b in buckets if remaining.get(b) and b not in last_bred]
        if not eligible:
            day += 1
            last_bred = set()  # a full rest day resets the alternation clock
            continue
        chosen = _pick_today(eligible, remaining, max_bucks_per_day, rng)
        schedule[day] = [remaining[b].pop(0) for b in chosen]
        for b in chosen:
            if not remaining[b]:
                del remaining[b]
        last_bred = set(chosen)
        day += 1
    return schedule


def _pick_today(
    eligible: list[str],
    remaining: dict[str, list[Pairing]],
    max_bucks_per_day: int,
    rng: random.Random | None,
) -> list[str]:
    """Choose today's breeders from the eligible bucks (busiest first).

    Without a day cap the greedy normally breeds every eligible buck (compresses
    the round); with probability 1/2 it instead HOLDS BACK the lightest buck so
    tomorrow still has an eligible breeder (avoids an avoidable idle day). The
    multi-start search samples both choices and the best (fewest days, then
    fewest idle days) wins. The hold-back never fires when every eligible buck
    would finish today, when only one buck is eligible, or when the day cap
    already limits the set (capacity-bound: breed the busiest).
    """
    ordered = sorted(eligible, key=lambda b: (-len(remaining[b]), b))
    if max_bucks_per_day > 0 and len(ordered) > max_bucks_per_day:
        return ordered[:max_bucks_per_day]
    all_finish = all(len(remaining[b]) == 1 for b in ordered)
    if len(ordered) >= 2 and not all_finish and rng is not None and rng.random() < 0.5:
        return ordered[:-1]  # hold back the lightest to cover tomorrow
    return ordered


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
    # Does per BUCK (a buck servicing k does spans 2k-1 days). Keyed on sire,
    # NOT dam — each dam appears once, so keying on dam collapsed all loads to
    # 1 and under-counted the estimate (issue #37).
    per_buck = Counter(p.sire for p in pairings)
    # A buck servicing k does spans 2k-1 days (k breed days + (k-1) rest days).
    buck_spans = [2 * k - 1 for k in per_buck.values()]

    # Batch bucks (arbitrary order) into groups of capacity; batch span = max.
    total = 0
    for i in range(0, len(buck_spans), buck_batch_capacity):
        batch = buck_spans[i : i + buck_batch_capacity]
        total += max(batch)
    return total
