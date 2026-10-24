"""Phase 6: security + edge-case tests (path-traversal guard, empty/single-buck)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from wabbitry_pairing_optimizer.config import (
    ConfigError,
    OutputConfig,
    load_config,
)
from wabbitry_pairing_optimizer.schedule import build_schedule, schedule_days

# --- Path-traversal guard on output artifact filenames (config) ---


def test_output_filenames_reject_traversal() -> None:
    """Absolute paths and `..` segments are rejected in artifact filenames."""
    for bad in ("/etc/passwd", "../escape.json", "sub/wabbitry.json", "..\\x"):
        with pytest.raises(ValidationError):
            OutputConfig(report_json=bad)
        with pytest.raises(ValidationError):
            OutputConfig(log_filename=bad)


def test_output_filenames_accept_plain() -> None:
    """Plain single-segment names still load fine."""
    c = OutputConfig(report_json="wabbitry-report.json")
    assert c.report_json == "wabbitry-report.json"


def test_load_config_rejects_traversal_as_configerror(tmp_path) -> None:
    """A TOML config with a traversal filename surfaces as ConfigError on load."""
    cfg = tmp_path / "cfg.toml"
    cfg.write_text('[output]\nreport_json = "../../hacked.json"\n', encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(cfg)


# --- Edge cases: empty pools, single buck ---


def test_empty_pairings_edge() -> None:
    """Empty pairing set yields an empty schedule and zero length."""
    assert build_schedule([], 4) == {}
    assert schedule_days([], 4) == 0


def test_single_buck_all_does() -> None:
    """One buck servicing every doe breeds every OTHER day (alternation)."""
    from wabbitry_pairing_optimizer.models import Pairing

    pairs = [
        Pairing(
            sire="yaz",
            dam=f"d{i}",
            pair_type="outcross",
            kinship_r=0.0,
            tier_penalty=0.0,
            score_r=0.0,
            score_doe_history=0.0,
            final_score=0.0,
        )
        for i in range(5)
    ]
    sched = build_schedule(pairs, 2)
    assert sorted(sched) == [1, 3, 5, 7, 9]  # 5 does, one every other day
    for _d, ps in sched.items():
        assert all(p.sire == "yaz" for p in ps)
        assert len(ps) == 1


def test_all_sibling_round_still_solves() -> None:
    """A closed pool where every doe is a full-sibling of the only buck still
    produces a valid solution (sibling=last resort, not a hard failure)."""
    from wabbitry_pairing_optimizer.config import load_config
    from wabbitry_pairing_optimizer.load_breeders import load_breeders
    from wabbitry_pairing_optimizer.load_litters import load_litters
    from wabbitry_pairing_optimizer.solve import solve

    cfg = load_config("data/config.toml")
    cfg = cfg.model_copy(
        update={
            "optimization": cfg.optimization.model_copy(
                update={"seed": 1, "min_runs": 20, "stall_limit": 5}
            )
        }
    )
    # All-sibling construct: every doe shares the same sire+dam as the buck.
    roster = load_breeders("data/breeders.json")
    fake = []
    for r in roster:
        if r.strain == "TAMUK" and not r.is_buck:
            # force all TAMUK does to be full-sibs of buck 'willy'
            fake.append(r.model_copy(update={"sire": "zeek", "dam": "abigail"}))
    rest = [r for r in roster if r.strain != "TAMUK" or r.is_buck]
    combined = rest + fake
    litters = load_litters("data/litters", known_rabbits={b.name for b in combined})
    sol = solve(combined, litters, cfg)  # should not raise; all does assigned
    assert len(sol.pairings) >= 1
    # Every ACTIVE TAMUK doe is either paired or reported unbred (solver
    # completes even under a forced all-sibling constraint — sibling last resort).
    tamuk_does = {
        r.name for r in combined if r.strain == "TAMUK" and not r.is_buck and not r.culled
    }
    paired_does = {p.dam for p in sol.pairings}
    assert tamuk_does <= (paired_does | set(sol.unbred_does))
