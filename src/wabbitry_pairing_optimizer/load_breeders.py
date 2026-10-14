"""Load and validate the breeding roster (design §2, Phase 1).

Loads ``data/breeders.json`` into a list of ``Breeder`` models, validates the
foreign keys (sire/dam resolve, possibly to a culled rabbit), enforces the
lowercase-identifier rule, checks for duplicate names, verifies every recipe
sums to 1.0, and fails loudly (not with silent fixes) on bad data.

Single concern: roster I/O + integrity validation.
"""

from __future__ import annotations

import json
from pathlib import Path

from wabbitry_pairing_optimizer.models import Breeder

__all__ = ["BreedersError", "load_breeders"]


class BreedersError(Exception):
    """Raised when the breeders file is missing, malformed, or fails integrity."""


def load_breeders(path: str | Path = "data/breeders.json") -> list[Breeder]:
    """Load and validate the roster at ``path`` into ``Breeder`` models.

    Args:
        path: Path to breeders.json.

    Returns:
        The validated roster.

    Raises:
        BreedersError: Any integrity failure (missing file, bad JSON, a parent
            name that does not resolve, a duplicate name, a recipe not summing
            to 1.0, or a non-lowercase identifier).
    """
    p = Path(path)
    if not p.is_file():
        raise BreedersError(f"breeders file not found: {p}")
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BreedersError(f"invalid JSON in {p}: {exc}") from exc
    if not isinstance(raw, list):
        raise BreedersError(f"{p}: expected a JSON list of rabbits")

    names: set[str] = set()
    breeders: list[Breeder] = []
    for item in raw:
        if not isinstance(item, dict) or "name" not in item:
            raise BreedersError(f"{p}: list item missing 'name': {item!r}")
        name = str(item["name"])
        if name != name.lower():
            raise BreedersError(f"{p}: identifier not lowercase: {name!r}")
        if name in names:
            raise BreedersError(f"{p}: duplicate rabbit name: {name}")
        names.add(name)
        breeders.append(Breeder(**item))

    _validate_parents(breeders, p)
    _validate_recipes(breeders, p)
    return breeders


def _validate_parents(breeders: list[Breeder], p: Path) -> None:
    """Every sire/dam must resolve to a known rabbit (culled parents are valid)."""
    known = {b.name for b in breeders}
    for b in breeders:
        for parent in (b.sire, b.dam):
            if parent is not None and parent not in known:
                raise BreedersError(f"{p}: {b.name!r} references unknown parent {parent!r}")


def _validate_recipes(breeders: list[Breeder], p: Path) -> None:
    """Every recipe must sum to 1.0 over its (known) ancestor keys."""
    known = {b.name for b in breeders}
    for b in breeders:
        recipe = b.recipe
        if abs(sum(recipe.values()) - 1.0) > 1e-9:
            raise BreedersError(
                f"{p}: {b.name!r} recipe sums to {sum(recipe.values()):.6f}, not 1.0"
            )
        unknown = set(recipe) - known
        if unknown:
            raise BreedersError(
                f"{p}: {b.name!r} recipe references unknown ancestors {sorted(unknown)}"
            )
