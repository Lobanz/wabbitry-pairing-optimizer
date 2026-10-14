"""Wabbitry pairing optimizer: least-bad breeding pairings."""

from wabbitry_pairing_optimizer.models import Breeder, Pairing, PairingReport
from wabbitry_pairing_optimizer.pairing import (
    EXCLUDED_STRAIN,
    PENALTY_LINE_BRED,
    PENALTY_OUTCROSS,
    PENALTY_SIBLING,
    YAZ_MIN_LITTERS,
    load_breeders,
    optimize_pairings,
)

__all__ = [
    "Breeder",
    "Pairing",
    "PairingReport",
    "load_breeders",
    "optimize_pairings",
    "EXCLUDED_STRAIN",
    "PENALTY_LINE_BRED",
    "PENALTY_OUTCROSS",
    "PENALTY_SIBLING",
    "YAZ_MIN_LITTERS",
]
