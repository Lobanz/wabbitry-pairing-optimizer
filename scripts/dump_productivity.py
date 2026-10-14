#!/usr/bin/env python3
"""Dev tool: dump the doe productivity index for operator review (Phase 2).

Prints each active doe's productivity index (size + consistency, blended with
dam by evidence) so the operator can eyeball which does are the most reliable
producers before the solver builds on it.

Usage:
    python scripts/dump_productivity.py [data/breeders.json] [data/litters]
"""

from __future__ import annotations

import sys
from pathlib import Path

from wabbitry_pairing_optimizer import load_breeders, load_config, load_litters
from wabbitry_pairing_optimizer.productivity import doe_production_scores

REPO = Path(__file__).resolve().parents[1]
BREEDERS = REPO / "data" / "breeders.json"
LITTERS = REPO / "data" / "litters"
CFG = REPO / "data" / "config.toml"


def main() -> int:
    """Print the productivity index for every active doe, ranked."""
    breeders_path = Path(sys.argv[1]) if len(sys.argv) > 1 else BREEDERS
    litters_path = Path(sys.argv[2]) if len(sys.argv) > 2 else LITTERS

    roster = load_breeders(breeders_path)
    cfg = load_config(CFG)
    litters = load_litters(litters_path, known_rabbits={b.name for b in roster})

    scores = doe_production_scores(roster, litters, cfg.productivity)
    by = {b.name: b for b in roster}

    print(f"# Doe productivity index (config: size_w={cfg.productivity.size_weight}, "
          f"consistency_w={cfg.productivity.consistency_weight}, "
          f"K={cfg.productivity.evidence_k}, trim={cfg.productivity.outlier_trim}:{cfg.productivity.outlier_method})")
    print(f"# Higher = more reliable producer (own litters, blended with dam by evidence)\n")

    header = f"{'doe':<10}{'strain':<8}{'idx':>7}  {'own_n':>5}  {'dam':<9}{'dam_n':>5}"
    print(header)
    print("-" * len(header))
    for name in sorted(scores, key=lambda n: -scores[n]):
        b = by[name]
        own_n = sum(1 for l in litters if l.dam == name)
        dam_n = sum(1 for l in litters if l.dam == b.dam) if b.dam else 0
        print(f"{name:<10}{b.strain:<8}{scores[name]:>7.3f}  {own_n:>5}  "
              f"{(b.dam or '-'):<9}{dam_n:>5}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
