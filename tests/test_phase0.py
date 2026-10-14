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
    for b in breeders:
        assert b.strain in {"M70", "TAMUK", "Composite"}


def test_roster_strain_split_matches_design() -> None:
    """The active roster matches the design's strain split (M70 + TAMUK only).

    Guards against a strain count drifting or a Composite sneaking in as active.

    NOTE (open item): data lists 4 active TAMUK bucks incl. ``vincent``
    (TAMUK, not Composite). The design described Vincent as the excluded
    Composite "diversity hire"; whether vincent breeds is UNRESOLVED and flagged
    at the Phase 0 gate. The test pins the data as-is (4 bucks) until ruled.
    """
    raw = json.loads((DATA / "breeders.json").read_text(encoding="utf-8"))
    active = [Breeder(**i) for i in raw if not i.get("culled")]
    m70 = [b for b in active if b.strain == "M70"]
    tamuk = [b for b in active if b.strain == "TAMUK"]
    comp = [b for b in active if b.strain == "Composite"]
    assert not comp, "Composite must be excluded from the active pool"
    # Design split (as of data): 7 M70 does + 3 M70 bucks, 6 TAMUK does + 4 TAMUK bucks.
    assert len([b for b in m70 if not b.is_buck]) == 7
    assert len([b for b in m70 if b.is_buck]) == 3
    assert len([b for b in tamuk if not b.is_buck]) == 6
    assert len([b for b in tamuk if b.is_buck]) == 4


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
