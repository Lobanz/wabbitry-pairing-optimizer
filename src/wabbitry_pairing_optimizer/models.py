"""Pydantic models for the wabbitry pairing optimizer.

Defines the breeder record (with parentage and culled/founder flags) and the
pairing result that the optimizer produces.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Breeder(BaseModel):
    """A rabbit in the breeding stock.

    Attributes:
        name: Unique identifier for the rabbit.
        breed: Combined strain + breed label, e.g. ``"M70 NZW"`` or
            ``"TAMUK NZW"``. ``"TAMUK Composite"`` is a non-pure strain that
            is excluded from the breeding program.
        gender: ``"M"`` (buck) or ``"F"`` (doe).
        siblings: Names of known sibling rabbits (full or half, approximate).
        culled: True if the rabbit is removed from the active breeding pool
            (e.g. freezer) but kept for pedigree reference.
        founder: True if parentage is unknown/irrelevant and the rabbit is
            treated as an unrelated founder.
        sire: Name of the sire (father), or None if unknown.
        dam: Name of the dam (mother), or None if unknown.
        parentage_uncertain: True if sire/dam are a best guess, not confirmed.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    breed: str
    gender: str
    siblings: list[str] = []
    culled: bool = False
    founder: bool = False
    sire: str | None = None
    dam: str | None = None
    parentage_uncertain: bool = False

    @property
    def is_buck(self) -> bool:
        """Return True if this rabbit is male."""
        return self.gender == "M"

    @property
    def strain(self) -> str:
        """Return the strain portion of the breed (e.g. ``"M70"``)."""
        return self.breed.split()[0]


class Pairing(BaseModel):
    """A single buck x doe breeding assignment for the next round.

    Attributes:
        sire: Name of the assigned buck.
        dam: Name of the assigned doe.
        kinship: Human-readable kinship description (e.g. ``"outcross"``,
            ``"line-bred"``, or ``"siblings"``).
        penalty: Numeric kinship penalty (lower is less related / better).
    """

    model_config = ConfigDict(frozen=True)

    sire: str
    dam: str
    kinship: str
    penalty: int


class PairingReport(BaseModel):
    """The full optimizer output for one breeding round.

    Attributes:
        pairings: The list of buck x doe assignments.
        unbred_does: Does that could not be assigned a buck.
        total_penalty: Sum of kinship penalties across all pairings.
    """

    model_config = ConfigDict(frozen=True)

    pairings: list[Pairing]
    unbred_does: list[str]
    total_penalty: int
