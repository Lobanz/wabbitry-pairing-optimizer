"""Phase 5 schedule-calendar tests: build_schedule invariants (mutation-verifiable)."""

from __future__ import annotations

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


def test_single_buck_consecutive_days() -> None:
    """A lone buck with k does breeds one per day, consecutive days."""
    round_pairs = [_p("yaz", "betty"), _p("yaz", "lily"), _p("yaz", "kiki")]
    sched = build_schedule(round_pairs, 4)
    days = sorted(sched)
    assert days == [1, 2, 3]  # operator inserts rest days; schedule is day batches
    # Every day has exactly that one buck.
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


def test_all_bucks_per_day_minimizes_days() -> None:
    """Unlimited cap: round length == the heaviest single buck load."""
    round_pairs = [
        _p("a", "a1"),
        _p("a", "a2"),
        _p("a", "a3"),
        _p("b", "b1"),
        _p("b", "b2"),
        _p("c", "c1"),
    ]
    sched = build_schedule(round_pairs, 0)  # unlimited
    # Heaviest buck (a) has 3 does -> 3 days.
    assert sorted(sched) == [1, 2, 3]
    # Heaviest buck breeds every day until its does are done.
    for day in (1, 2, 3):
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
