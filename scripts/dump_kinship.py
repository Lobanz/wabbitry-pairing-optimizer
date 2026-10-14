#!/usr/bin/env python3
"""Dev tool: dump the kinship (r) matrix + sibling sets for operator review.

Phase 1 reassessment deliverable. Prints the r value for every pair of ACTIVE
(breeding-pool) rabbits, plus the derived full-sibling sets, so the operator can
eyeball whether the kinship model reflects reality before the solver builds on it.

Usage:
    python scripts/dump_kinship.py [data/breeders.json]
"""

from __future__ import annotations

import sys
from pathlib import Path

from wabbitry_pairing_optimizer import (
    coancestry_matrix_r,
    full_sibling_sets,
    load_breeders,
    load_config,
)

REPO = Path(__file__).resolve().parents[1]
DEFAULT_BREEDERS = REPO / "data" / "breeders.json"
DEFAULT_CONFIG = REPO / "data" / "config.toml"


def main() -> int:
    """Print the kinship table for active breeding-pool rabbits."""
    breeders_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BREEDERS
    roster = load_breeders(breeders_path)
    cfg = load_config(DEFAULT_CONFIG)

    # Active breeding pool: not culled, not Composite.
    active = [b for b in roster if not b.culled and not b.is_composite]
    active_names = {b.name for b in active}

    mat = coancestry_matrix_r(roster, cfg.kinship)

    print(f"# Kinship matrix: active breeding pool ({len(active)} rabbits)")
    print(
        f"# Config: sister_factor={cfg.kinship.sister_factor} "
        f"outcross_r_max={cfg.kinship.outcross_r_max}"
    )
    print("# r = coefficient of relationship (0.0 unrelated .. 0.5 full-sib; self=1.0)\n")

    # Print symmetric table for active rabbits.
    names = sorted(active_names)
    header = "     " + " ".join(f"{n:>6}" for n in names)
    print(header)
    for a in names:
        row = [f"{a:>6}"]
        for b in names:
            if a == b:
                row.append("  1.00")
            else:
                key = (a, b) if a < b else (b, a)
                r = mat.get(key, 0.0)
                row.append(f"{r:6.2f}")
        print("  ".join(row))

    print("\n# Derived full-sibling sets (same sire+dam):")
    for sibset in full_sibling_sets(roster):
        if any(n in active_names for n in sibset):
            print("   " + ", ".join(sibset))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
