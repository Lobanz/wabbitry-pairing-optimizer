"""Wabbitry pairing optimizer: least-bad breeding pairings.

Public API: the data models, the typed config, and (once implemented in later
phases) the solver, kinship, productivity, and report functions.
"""

#: Single source of truth for the package version (issue #40): hatch reads it
#: via ``dynamic = ["version"]`` + ``[tool.hatch.version] path``, and the CLI
#: ``--version`` returns it.
__version__ = "0.2.0"

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
    PairTier,
    RelationshipKind,
    coancestry_matrix_r,
    full_sibling_sets,
    relationship_kind,
    tier_for_pair,
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
from wabbitry_pairing_optimizer.productivity import (
    doe_production_scores,
    productivity_index,
)
from wabbitry_pairing_optimizer.recipe import (
    RecipeError,
    verify_recipes,
)
from wabbitry_pairing_optimizer.schedule import build_schedule
from wabbitry_pairing_optimizer.scoring import (
    full_solution_score,
    per_pairing_score,
)
from wabbitry_pairing_optimizer.solve import solve

__all__ = [
    "__version__",
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
    "PairTier",
    "PerPairingConfig",
    "ProductivityConfig",
    "RecipeError",
    "RelationshipKind",
    "ScoringConfig",
    "Solution",
    "SolutionScore",
    "TierPenaltyConfig",
    "build_schedule",
    "coancestry_matrix_r",
    "doe_production_scores",
    "full_sibling_sets",
    "full_solution_score",
    "load_breeders",
    "load_config",
    "load_litters",
    "per_pairing_score",
    "productivity_index",
    "relationship_kind",
    "solve",
    "tier_for_pair",
    "tier_for_r",
    "verify_recipes",
]
