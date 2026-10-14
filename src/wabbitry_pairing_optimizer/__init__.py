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
from wabbitry_pairing_optimizer.kinship import (
    coancestry_matrix_r,
    full_sibling_sets,
    tier_for_r,
)
from wabbitry_pairing_optimizer.load_breeders import (
    BreedersError,
    load_breeders,
)
from wabbitry_pairing_optimizer.load_litters import (
    Litter,
    LittersError,
    load_litters,
)
from wabbitry_pairing_optimizer.models import (
    Breeder,
    Pairing,
    PairingReport,
    Solution,
    SolutionScore,
)
from wabbitry_pairing_optimizer.recipe import (
    RecipeError,
    verify_recipes,
)

__all__ = [
    "Breeder",
    "BreedersError",
    "Config",
    "ConfigError",
    "FullSolutionConfig",
    "KinshipConfig",
    "Litter",
    "LittersError",
    "OptimizationConfig",
    "OutputConfig",
    "PairabilityConfig",
    "Pairing",
    "PairingReport",
    "PerPairingConfig",
    "ProductivityConfig",
    "RecipeError",
    "ScoringConfig",
    "Solution",
    "SolutionScore",
    "TierPenaltyConfig",
    "coancestry_matrix_r",
    "full_sibling_sets",
    "load_breeders",
    "load_config",
    "load_litters",
    "tier_for_r",
    "verify_recipes",
]
