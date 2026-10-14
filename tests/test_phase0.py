"""Phase 0 tests: toolchain proof + config load + model validation.

These prove the foundation (design §9 config, §2 data model) before the
algorithm phases build on it. They also confirm the harness (pytest + mypy +
ruff) is green on the scaffold.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wabbitry_pairing_optimizer import load_config
from wabbitry_pairing_optimizer.config import ConfigError
from wabbitry_pairing_optimizer.models import Breeder

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA = REPO_ROOT / "data"


def test_config_loads_from_real_toml() -> None:
    """The shipped data/config.toml loads into a typed Config."""
    cfg = load_config(DATA / "config.toml")
    assert cfg.kinship.sister_factor == 0.5
    assert cfg.kinship.outcross_r_max == 0.1
    assert cfg.optimization.min_runs == 500
    assert cfg.optimization.stall_limit == 100
    assert cfg.output.output_dir == "out"
    assert cfg.output.log_filename == "wabbitry-run.log"


def test_config_missing_file_raises() -> None:
    """A missing config file surfaces a clear ConfigError."""
    with pytest.raises(ConfigError):
        load_config(DATA / "does-not-exist.toml")


def test_config_invalid_toml_raises() -> None:
    """Invalid TOML content surfaces a ConfigError, not a crash."""
    bad = REPO_ROOT / "tests" / "_bad_config.toml"
    bad.write_text("not: = [valid", encoding="utf-8")
    try:
        with pytest.raises(ConfigError):
            load_config(bad)
    finally:
        bad.unlink(missing_ok=True)


def test_breeder_round_trip_real_data() -> None:
    """Every rabbit in breeders.json validates; the roster matches expectations.

    Pins the real roster (28 rabbits) so an accidental add/remove/duplicate of a
    breeder is caught, not just any-validates.
    """
    raw = json.loads((DATA / "breeders.json").read_text(encoding="utf-8"))
    breeders = [Breeder(**item) for item in raw]
    assert len(breeders) == 28, f"expected 28 rabbits, got {len(breeders)}"
    names = [b.name for b in breeders]
    assert len(names) == len(set(names)), "duplicate rabbit names"
    # breeding pools are M70 and TAMUK; Composite is a separate excluded breed.
    for b in breeders:
        assert b.strain in {"M70", "TAMUK"}


def test_roster_breeding_pools_match_design() -> None:
    """The breeding pools match the design (M70 NZW + TAMUK NZW only).

    Vincent is TAMUK Composite — a SEPARATE, excluded breed (the "diversity
    hire"), NOT in the TAMUK breeding pool. So the TAMUK pool is 3 bucks, not 4.
    """
    raw = json.loads((DATA / "breeders.json").read_text(encoding="utf-8"))
    breeders = [Breeder(**i) for i in raw]
    active = [b for b in breeders if not b.culled]

    # Composite (any non-NZW breed) is absent from the active breeding pools.
    composite = [b for b in active if b.is_composite]
    assert [b.name for b in composite] == ["vincent"], (
        f"expected only vincent as Composite, got {[b.name for b in composite]}"
    )
    assert all(b.is_composite for b in composite)
    assert not any(b.is_composite for b in breeders if b.name != "vincent"), (
        "only vincent should be Composite"
    )

    # Breeding pools: M70 NZW (3B/7D) and TAMUK NZW (3B/6D).
    m70 = [b for b in active if b.strain == "M70" and not b.is_composite]
    tamuk = [b for b in active if b.strain == "TAMUK" and not b.is_composite]
    assert len([b for b in m70 if not b.is_buck]) == 7
    assert len([b for b in m70 if b.is_buck]) == 3
    assert len([b for b in tamuk if not b.is_buck]) == 6
    assert len([b for b in tamuk if b.is_buck]) == 3
    # Vincent is present in the roster but excluded from breeding.
    assert "vincent" not in [b.name for b in m70 + tamuk]


def test_vincent_is_composite_and_excluded() -> None:
    """Vincent is the only Composite; Breeder flags him excluded from breeding."""
    raw = json.loads((DATA / "breeders.json").read_text(encoding="utf-8"))
    vin = [b for b in raw if b["name"] == "vincent"][0]
    v = Breeder(**vin)
    assert v.is_composite is True
    assert v.strain == "TAMUK"  # origin label, but Composite breed → excluded
    assert not v.culled  # healthy, just not part of the breeding program


def test_recipe_sums_to_one_on_real_data() -> None:
    """Every breeder's recipe sums to 1.0 (design: every ancestor, total 1.0)."""
    raw = json.loads((DATA / "breeders.json").read_text(encoding="utf-8"))
    for item in raw:
        r = item.get("recipe", {})
        assert abs(sum(r.values()) - 1.0) < 1e-9, f"recipe for {item['name']} does not sum to 1.0"


def test_breeder_model_frozen() -> None:
    """Models are immutable (safe across the decoupled module DAG)."""
    b = Breeder(name="yaz", breed="M70 NZW", gender="M")
    with pytest.raises(ValueError):
        b.name = "zeek"  # type: ignore[misc]


def test_gender_consistency_of_parents() -> None:
    """Every sire is a buck and every dam is a doe in the real roster.

    Regression test: fiona's pedigree had dam/sire swapped (sire=ester [F],
    dam=willy [M]); fixed to sire=willy, dam=ester. load_breeders now validates.
    """
    from wabbitry_pairing_optimizer.load_breeders import load_breeders

    roster = load_breeders(DATA / "breeders.json")
    by = {b.name: b for b in roster}
    for b in roster:
        if b.sire is not None:
            assert by[b.sire].gender == "M", f"{b.name} sire {b.sire} is not a buck"
        if b.dam is not None:
            assert by[b.dam].gender == "F", f"{b.name} dam {b.dam} is not a doe"
    # The specific former inversion is now correct.
    assert by["fiona"].sire == "willy"
    assert by["fiona"].dam == "ester"
