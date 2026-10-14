"""Wabbitry pairing optimizer: least-bad breeding pairings.

Public API: the data models, the typed config, and (once implemented in later
phases) the solver, kinship, productivity, and report functions.
"""

from wabbitry_pairing_optimizer.config import (
    Config,
    ConfigError,
    FullSolutionConfig,
    KinshipConfig,
    OptimizationConfig,
    OutputConfig,
    PairabilityConfig,
    PerPairingConfig,
    ProductivityConfig,
    ScoringConfig,
    TierPenaltyConfig,
    load_config,
)
from wabbitry_pairing_optimizer.models import (
    Breeder,
    Pairing,
    PairingReport,
    Solution,
    SolutionScore,
)

__all__ = [
    "Breeder",
    "Config",
    "ConfigError",
    "FullSolutionConfig",
    "KinshipConfig",
    "OptimizationConfig",
    "OutputConfig",
    "PairabilityConfig",
    "Pairing",
    "PairingReport",
    "PerPairingConfig",
    "ProductivityConfig",
    "ScoringConfig",
    "Solution",
    "SolutionScore",
    "TierPenaltyConfig",
    "load_config",
]
