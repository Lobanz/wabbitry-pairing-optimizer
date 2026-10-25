"""Phase 5 schedule-calendar tests: build_schedule invariants (mutation-verifiable)."""

from __future__ import annotations

import random

from wabbitry_pairing_optimizer.models import Pairing
from wabbitry_pairing_optimizer.schedule import build_schedule, schedule_days


def _p(sire: str, dam: str) -> Pairing:
    return Pairing(
        sire=sire,
        dam=dam,
        pair_type="outcross",
        kinship_r=0.0,
        tier_penalty=0.0,
        score_r=0.0,
        score_doe_history=0.0,
        final_score=0.0,
    )


def test_empty_round() -> None:
    assert build_schedule([], 4) == {}
    assert schedule_days([], 4) == 0


def test_schedule_days_per_buck() -> None:
    """Length estimate keys on BUCK load (issue #37 regression pin)."""
    round_pairs = (
        [_p("yaz", f"y{i}") for i in range(3)]
        + [_p("zack", f"z{i}") for i in range(3)]
        + [_p("uno", "u1")]
        + [_p("vader", f"v{i}") for i in range(2)]
        + [_p("willy", f"w{i}") for i in range(2)]
        + [_p("xerces", f"x{i}") for i in range(2)]
    )
    # yaz/zack 3 does -> 5 days; uno 1 -> 1; vader/willy/xerces 2 -> 3 each.
    # Batches of 4: [5,5,5,1] -> 5, then [3,3,3] -> 3. Total 8 (was 4 pre-fix).
    assert schedule_days(round_pairs, 4) == 8


def test_single_buck_spaced_days() -> None:
    """A lone buck with k does breeds every OTHER day (alternation in model)."""
    round_pairs = [_p("yaz", "betty"), _p("yaz", "lily"), _p("yaz", "kiki")]
    sched = build_schedule(round_pairs, 4, rng=random.Random(5))  # noqa: S311 - seeded PRNG for reproducible schedules
    days = sorted(sched)
    assert days == [1, 3, 5]  # rest days are now part of the schedule
    # Every breeding day has exactly that one buck.
    for d in days:
        assert sched[d][0].sire == "yaz"
        assert len(sched[d]) == 1


def test_max_bucks_per_day_respected() -> None:
    """No single day has more distinct bucks than the cap."""
    round_pairs = [
        _p("a", "a1"),
        _p("a", "a2"),
        _p("b", "b1"),
        _p("b", "b2"),
        _p("c", "c1"),
    ]
    sched = build_schedule(round_pairs, max_bucks_per_day=2)
    for pairs in sched.values():
        assert len({p.sire for p in pairs}) <= 2
    # All does assigned exactly once.
    assigned = [p.dam for ps in sched.values() for p in ps]
    assert sorted(assigned) == sorted(["a1", "a2", "b1", "b2", "c1"])


def test_all_bucks_per_day_alternating() -> None:
    """Unlimited cap: round length == the heaviest buck's alternating span."""
    round_pairs = [
        _p("a", "a1"),
        _p("a", "a2"),
        _p("a", "a3"),
        _p("b", "b1"),
        _p("b", "b2"),
        _p("c", "c1"),
    ]
    sched = build_schedule(round_pairs, 0)  # unlimited, baseline pass
    # Heaviest buck (a) has 3 does -> spans 2*3-1 = 5 days, every other day.
    assert sorted(sched) == [1, 3, 5]
    # Heaviest buck breeds every OTHER day until its does are done.
    for day in (1, 3, 5):
        assert any(p.sire == "a" for p in sched[day])
    all_pairs = [p.dam for ps in sched.values() for p in ps]
    assert sorted(all_pairs) == sorted(["a1", "a2", "a3", "b1", "b2", "c1"])


def test_capped_takes_longer_than_unlimited() -> None:
    """Capping bucks/day spreads the round over more days than unlimited."""
    round_pairs = [_p("a", f"a{i}") for i in range(4)] + [_p("b", f"b{i}") for i in range(4)]
    unlimited = build_schedule(round_pairs, 0)
    capped = build_schedule(round_pairs, 1)  # one buck/day -> serialized
    assert max(unlimited) < max(capped)


def test_round_length_is_max_day() -> None:
    """Every pair is scheduled; round length is the highest day used."""
    round_pairs = [
        _p("a", "a1"),
        _p("a", "a2"),
        _p("a", "a3"),
        _p("b", "b1"),
        _p("b", "b2"),
    ]
    sched = build_schedule(round_pairs, 2)
    n_pairs = sum(len(v) for v in sched.values())
    assert n_pairs == len(round_pairs)
    # No empty trailing days after the last breeding day.
    assert max(sched) in sched


def test_deterministic() -> None:
    """Same input + cap produces an identical calendar every call."""
    round_pairs = [
        _p("a", "a1"),
        _p("a", "a2"),
        _p("b", "b1"),
        _p("b", "b2"),
        _p("c", "c1"),
        _p("c", "c2"),
        _p("c", "c3"),
    ]
    s1 = build_schedule(round_pairs, 2)
    s2 = build_schedule(round_pairs, 2)
    assert [[p.dam for p in v] for _, v in sorted(s1.items())] == [
        [p.dam for p in v] for _, v in sorted(s2.items())
    ]


def test_no_buck_consecutive_days() -> None:
    """Property: no buck breeds on two consecutive days, any cap or load mix."""
    sets = [
        [_p("a", f"a{i}") for i in range(3)],
        [_p("a", f"a{i}") for i in range(3)] + [_p("b", "b1")],
        [_p("a", f"a{i}") for i in range(3)]
        + [_p("b", f"b{i}") for i in range(3)]
        + [_p("c", "c1")],
        [_p("a", f"a{i}") for i in range(5)] + [_p("b", f"b{i}") for i in range(2)],
        [_p("a", f"a{i}") for i in range(4)] + [_p("b", f"b{i}") for i in range(4)],
    ]
    for round_pairs in sets:
        for cap in (0, 1, 2, 4):
            sched = build_schedule(round_pairs, cap, rng=random.Random(7))  # noqa: S311 - seeded PRNG for reproducible schedules
            by_day = {d: {p.sire for p in ps} for d, ps in sched.items()}
            for d in sorted(by_day):
                for b in by_day[d]:
                    assert b not in by_day.get(d - 1, set())
            # Every breeding is scheduled exactly once.
            assigned = [p.dam for ps in sched.values() for p in ps]
            assert sorted(assigned) == sorted(p.dam for p in round_pairs)


def test_optimal_alternation_a3_b1() -> None:
    """The counter-example that killed pure greedy: 5 days, single idle day."""
    round_pairs = [_p("a", "a1"), _p("a", "a2"), _p("a", "a3"), _p("b", "b1")]
    sched = build_schedule(round_pairs, 0, rng=random.Random(42))  # noqa: S311 - seeded PRNG for reproducible schedules
    assert sorted(sched) == [1, 2, 3, 5]  # 5 round days, day 4 idle


def test_optimal_alternation_a3_b3_c1() -> None:
    """Three bucks interleave to 5 days with a single idle day."""
    round_pairs = (
        [_p("a", f"a{i}") for i in range(3)]
        + [_p("b", f"b{i}") for i in range(3)]
        + [_p("c", "c1")]
    )
    sched = build_schedule(round_pairs, 0, rng=random.Random(42))  # noqa: S311 - seeded PRNG for reproducible schedules
    assert sorted(sched) == [1, 2, 3, 5]


def test_schedule_reproducible_with_seed() -> None:
    """Same seed produces an identical optimized calendar every call."""
    round_pairs = (
        [_p("a", f"a{i}") for i in range(3)]
        + [_p("b", f"b{i}") for i in range(2)]
        + [_p("c", "c1")]
    )
    s1 = build_schedule(round_pairs, 2, rng=random.Random(99))  # noqa: S311 - seeded PRNG for reproducible schedules
    s2 = build_schedule(round_pairs, 2, rng=random.Random(99))  # noqa: S311 - seeded PRNG for reproducible schedules
    assert [[p.dam for p in v] for _, v in sorted(s1.items())] == [
        [p.dam for p in v] for _, v in sorted(s2.items())
    ]
