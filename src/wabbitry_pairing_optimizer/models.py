"""Pydantic models for the wabbitry pairing optimizer.

Defines the typed data objects that flow through the program:

- ``Breeder``   — a rabbit in the breeding stock (design §2).
- ``Pairing``   — one buck×doe breeding assignment + its per-pairing score (§8).
- ``Solution``  — a complete assignment set for one round + its full-solution
  score breakdown (§8 tier 2) and schedule/pairability.
- ``PairingReport`` — the structured, dual-format output artifact (§7/§8).

Models are frozen (immutable) so they are safe to share across the decoupled
modules and can be hashed/compared for winner tracking.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Breeder(BaseModel):
    """A rabbit in the breeding stock.

    Attributes:
        name: Unique lowercase identifier.
        breed: Combined origin + breed, e.g. ``"M70 NZW"`` or ``"TAMUK NZW"``.
            For breeding, strain = the first token (``M70`` / ``TAMUK``).
            ``"TAMUK Composite"`` is a SEPARATE, excluded breed (kept as the
            "diversity hire", not part of the breeding program) — see
            ``is_composite``.
        gender: ``"M"`` (buck) or ``"F"`` (doe).
        culled: Removed from the active pool (e.g. freezer) but kept as a valid
            parent reference; excluded as a breeding candidate.
        founder: Parentage unknown/irrelevant; identity terminates ancestry.
        sire: Name of the sire (father), or None if unknown.
        dam: Name of the dam (mother), or None if unknown.
        founder_sisters: Founder does known to be siblings (sole sibling signal
            for founders, who have no recorded parents to derive from).
        recipe: Ancestor-percentage vector; every ancestor, sums to 1.0.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    breed: str
    gender: str
    culled: bool = False
    founder: bool = False
    sire: str | None = None
    dam: str | None = None
    founder_sisters: list[str] = Field(default_factory=list)
    recipe: dict[str, float] = Field(default_factory=dict)

    @property
    def is_buck(self) -> bool:
        """True if this is a buck (male)."""
        return self.gender == "M"

    @property
    def strain(self) -> str:
        """The strain portion of the breed, e.g. ``"M70"`` or ``"TAMUK"``.

        Strain is the first token of the breed label (used for pool grouping).
        It is distinct from Composite status: a ``"TAMUK Composite"`` rabbit has
        strain ``"TAMUK"`` but is excluded from breeding (see ``is_composite``).
        """
        return self.breed.split()[0]

    @property
    def is_composite(self) -> bool:
        """True if the breed label carries a ``Composite`` token.

        A Composite is not part of the pure breeding program (design §2/§3):
        it is kept for diversity but is excluded as a breeding candidate. The
        ``Composite`` token may appear anywhere in the label (e.g.
        ``"TAMUK Composite"``), so this is a token check, not the strain.
        """
        return "Composite" in self.breed.split()


class Pairing(BaseModel):
    """A single buck×doe breeding assignment (design §8 tier 1).

    Attributes:
        sire: Name of the assigned buck.
        dam: Name of the assigned doe.
        pair_type: Tier label — "outcross", "line_bred", or "sibling".
        kinship_r: Coefficient of relationship r (0.0–1.0) for this pair.
        tier_penalty: Tier penalty (config; 0 / 1 / 5 by default).
        score_r: Weighted r term of the per-pairing score.
        score_doe_history: Weighted doe-productivity term of the per-pairing score.
        final_score: The per-pairing weighted score (= score_r + score_doe_history).
        fixed: True if this pair was operator pre-decided (--pairs), not auto.
    """

    model_config = ConfigDict(frozen=True)

    sire: str
    dam: str
    pair_type: str
    kinship_r: float
    tier_penalty: float
    score_r: float
    score_doe_history: float
    final_score: float
    fixed: bool = False


class SolutionScore(BaseModel):
    """Full-solution score breakdown (design §8 tier 2).

    Each field is one weighted component; ``final`` is their sum.

    Attributes:
        sum_r: Weighted sum-of-r component (minimize inbreeding).
        sum_history: Weighted sum of doe-production-history component.
        unbred_penalty: Weighted penalty per unbred doe (order-trap artifact).
        sibling_penalty: Weighted penalty per forced full-sib last-resort pair.
        schedule_penalty: Weighted schedule-length penalty (operator labor).
        pairability: Weighted pairability term (mixed-pair availability count).
        final: Sum of all weighted components.
    """

    model_config = ConfigDict(frozen=True)

    sum_r: float = 0.0
    sum_history: float = 0.0
    unbred_penalty: float = 0.0
    sibling_penalty: float = 0.0
    schedule_penalty: float = 0.0
    pairability: float = 0.0
    final: float = 0.0


class Solution(BaseModel):
    """A complete assignment set for one round (design §8 tier 2).

    Attributes:
        pairings: All pairings, including any fixed (operator) pairs.
        unbred_does: Does that could not be assigned a buck.
        score: Full-solution score breakdown.
        schedule_days: Estimated round length in days.
        pairability_count: Number of mixed pairs the round's litters support.
    """

    model_config = ConfigDict(frozen=True)

    pairings: list[Pairing]
    unbred_does: list[str] = Field(default_factory=list)
    score: SolutionScore = Field(default_factory=SolutionScore)
    schedule_days: int = 0
    pairability_count: int = 0


class PairingReport(BaseModel):
    """The structured output artifact for one round (design §7/§8).

    The json render of this object is the agent-consumable source of truth; the
    markdown render is the human report of the same data.

    Attributes:
        breeders: The roster (for a self-contained report).
        solution: The winning pairing solution.
        fixed_pairs: Any operator pre-decided pairs that were supplied.
        kinship_table: The r matrix, keyed "sire|dam" -> r (and as data).
        doe_productivity: The doe productivity index table (as data).
    """

    model_config = ConfigDict(frozen=True)

    breeders: list[Breeder]
    solution: Solution
    fixed_pairs: list[Pairing] = Field(default_factory=list)
    kinship_table: dict[str, float] = Field(default_factory=dict)
    doe_productivity: dict[str, float] = Field(default_factory=dict)


__all__ = [
    "Breeder",
    "Pairing",
    "PairingReport",
    "Solution",
    "SolutionScore",
]
