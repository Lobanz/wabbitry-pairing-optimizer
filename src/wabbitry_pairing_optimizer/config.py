"""Load and validate the operator-policy TOML config (design §9).

Every tunable/opinion value lives in the TOML config file (default
``data/config.toml``). Precedence (2026-10-15), top wins:

    CLI params  >  config-file values  >  reasonable built-in defaults

This module owns the config-file layer and the built-in defaults; CLI overrides
are applied by the caller (``__main__``). Config parsing errors surface as a
clear ``ConfigError`` so the CLI can emit them structurally.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

__all__ = ["Config", "ConfigError", "load_config"]


class ConfigError(Exception):
    """Raised when the config file is missing, unparseable, or invalid."""


class KinshipConfig(BaseModel):
    """Kinship model knobs (design §5/§9).

    Attributes:
        sister_factor: Founder-sister factor S (default 0.5).
        outcross_r_max: r at/below which a pair is an outcross (default 0.1).
    """

    model_config = ConfigDict(frozen=True)

    sister_factor: float = 0.5
    outcross_r_max: float = 0.1


class ProductivityConfig(BaseModel):
    """Doe productivity index knobs (design §8/§9).

    Attributes:
        size_weight: Weight of avg-litter-size component.
        consistency_weight: Weight of consistency component.
        evidence_k: Blend constant K; w_own = own_count / (own_count + K).
        outlier_trim: Whether to trim outliers before averaging size.
        outlier_method: "iqr" or "zscore" for trimming litter outliers.
        outlier_threshold: Threshold for the outlier method (IQR mult / zscore sd).
    """

    model_config = ConfigDict(frozen=True)

    size_weight: float = 0.6
    consistency_weight: float = 0.4
    evidence_k: float = 2.0
    outlier_trim: bool = True
    outlier_method: str = "iqr"
    outlier_threshold: float = 1.5


class TierPenaltyConfig(BaseModel):
    """Pairing tier penalties (design §5/§9).

    Attributes:
        penalty_outcross: Score added for an outcross pair (0).
        penalty_line_bred: Score added for a line-bred pair (1).
        penalty_sibling: Score added for a full-sib pair (5).
    """

    model_config = ConfigDict(frozen=True)

    penalty_outcross: float = 0.0
    penalty_line_bred: float = 1.0
    penalty_sibling: float = 5.0


class PerPairingConfig(BaseModel):
    """Per-pairing scoring weights (design §8 tier 1).

    Attributes:
        weight_r: Weight on the r term.
        weight_doe_history: Weight on the doe-production-history term.
    """

    model_config = ConfigDict(frozen=True)

    weight_r: float = 1.0
    weight_doe_history: float = 1.0


class FullSolutionConfig(BaseModel):
    """Full-solution scoring weights (design §8 tier 2).

    Attributes:
        weight_sum_r: Weight on the sum-of-r component.
        weight_sum_history: Weight on the sum-of-doe-history component.
        weight_unbred: Weight (penalty) per unbred doe.
        weight_sibling: Weight (penalty) per forced full-sib pair.
        weight_schedule_length: Weight on round calendar length (operator labor).
        weight_pairability: Weight on the pairability term.
    """

    model_config = ConfigDict(frozen=True)

    weight_sum_r: float = 1.0
    weight_sum_history: float = 1.0
    weight_unbred: float = -5.0
    weight_sibling: float = -3.0
    weight_schedule_length: float = -0.3
    weight_pairability: float = 1.0


class PairabilityConfig(BaseModel):
    """Pairability metric knobs (design §4/§8).

    Attributes:
        mode: Swappable metric select — "availability" (default) or future mode.
    """

    model_config = ConfigDict(frozen=True)

    mode: str = "availability"


class OptimizationConfig(BaseModel):
    """Optimization loop knobs (design §6).

    Attributes:
        min_runs: Minimum runs before any stall-based stop can fire.
        stall_limit: Runs without a new winner after min_runs before stopping.
        seed: Fixed PRNG seed for reproducibility (0 = unset/random). Consistent
            nonzero seed (e.g. 42) when tuning weights so round changes reflect
            only the weight change, not shuffling noise.
        buck_batch_capacity: Max bucks the operator can watch concurrently.
    """

    model_config = ConfigDict(frozen=True)

    min_runs: int = 500
    stall_limit: int = 100
    seed: int = 0
    buck_batch_capacity: int = 4


class DiversityConfig(BaseModel):
    """Buck-diversity levers during auto pairing generation (design §6).

    Both knobs are INDEPENDENT levers that make spread reachable by the search
    (per operator 2026-10-15: diversity must be GENERATED, not only scored).
    They apply per-run, per-strain, to auto assignment only (fixed pairs are
    excluded from auto pools already). ``0`` / ``0.0`` disables each knob.

    Attributes:
        max_does_per_buck: Hard cap on how many does one buck may service in a
            round's auto assignment; a buck at the cap is removed from the
            candidate list for remaining does (0 = disabled). Blunt: can force
            a doe onto her 2nd-best buck, or leave a tight pool unbred.
        load_penalty: Soft score reduction each buck absorbs per doe it already
            holds in the current run, so the greedy spreads naturally while a
            buck can still concentrate when it is genuinely the only good
            match. Preferred lever (default 0.5); preserves least-bad, no
            unbred failure mode.
    """

    model_config = ConfigDict(frozen=True)

    max_does_per_buck: int = 0
    load_penalty: float = 0.5


class OutputConfig(BaseModel):
    """Result-artifact settings (design §8).

    Note: this is the *artifact* policy (where/names things are written). The
    CLI ``--output json|text`` emission-language flag is NOT a config param.

    Attributes:
        output_dir: Default destination for all result artifacts.
        report_json: Structured result filename (agents/software).
        report_md: Human markdown report filename.
        kinship_table_csv: r matrix standalone CSV filename.
        doe_productivity_csv: Doe productivity index standalone CSV filename.
        log_filename: Run log filename (written to the output dir, not stdout).
        log_level: Log level: DEBUG/INFO/WARNING/ERROR.
        log_format: "json" (JSON-lines) or "text".
    """

    model_config = ConfigDict(frozen=True)

    output_dir: str = "out"
    report_json: str = "wabbitry-report.json"
    report_md: str = "wabbitry-report.md"
    kinship_table_csv: str = "kinship-table.csv"
    doe_productivity_csv: str = "doe-productivity.csv"
    log_filename: str = "wabbitry-run.log"
    log_level: str = "INFO"
    log_format: str = "json"

    @field_validator(
        "report_json",
        "report_md",
        "kinship_table_csv",
        "doe_productivity_csv",
        "log_filename",
    )
    @classmethod
    def _filename_is_plain(cls, v: str) -> str:
        """Reject filenames that could escape the output dir (path traversal).

        Output artifact filenames are operator-supplied config, so a name with
        an absolute path, a `..` segment, or a path separator would redirect
        writes outside the intended ``output_dir``. Fail fast at load.
        """
        p = Path(v)
        if p.is_absolute() or any(part == ".." for part in p.parts):
            raise ValueError(f"output filename must be a plain name, got {v!r}")
        if "/" in v or "\\" in v or p.name != v:
            raise ValueError(f"output filename must be a single name, got {v!r}")
        return v


class Config(BaseModel):
    """The full operator-policy config (design §9)."""

    model_config = ConfigDict(frozen=True)

    kinship: KinshipConfig = Field(default_factory=KinshipConfig)
    productivity: ProductivityConfig = Field(default_factory=ProductivityConfig)
    scoring: ScoringConfig = Field(default_factory=lambda: ScoringConfig())
    pairability: PairabilityConfig = Field(default_factory=PairabilityConfig)
    optimization: OptimizationConfig = Field(default_factory=OptimizationConfig)
    diversity: DiversityConfig = Field(default_factory=DiversityConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


class ScoringConfig(BaseModel):
    """Scoring weights (design §8/§9): per-pairing + tier + full-solution."""

    model_config = ConfigDict(frozen=True)

    per_pairing: PerPairingConfig = Field(default_factory=PerPairingConfig)
    tier_penalty: TierPenaltyConfig = Field(default_factory=TierPenaltyConfig)
    full_solution: FullSolutionConfig = Field(default_factory=FullSolutionConfig)


def load_config(path: str | Path) -> Config:
    """Load and validate the TOML config at ``path`` into a typed ``Config``.

    Raises:
        ConfigError: If the file is missing, invalid TOML, or fails validation.
    """
    p = Path(path)
    if not p.is_file():
        raise ConfigError(f"config file not found: {p}")
    try:
        raw = tomllib.loads(p.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {p}: {exc}") from exc
    try:
        return Config.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"invalid config in {p}: {exc}") from exc


# Re-export the model namespace here so consumers import models via config or
# directly from models; models are the single source of truth.
__all__ = [
    "Config",
    "ConfigError",
    "DiversityConfig",
    "FullSolutionConfig",
    "KinshipConfig",
    "OptimizationConfig",
    "OutputConfig",
    "PairabilityConfig",
    "PerPairingConfig",
    "ProductivityConfig",
    "ScoringConfig",
    "TierPenaltyConfig",
    "load_config",
]
