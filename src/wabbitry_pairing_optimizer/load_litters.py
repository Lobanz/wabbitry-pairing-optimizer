"""Load and validate litter history (design §2, Phase 1).

Loads all ``data/litters/*.json`` files (one per breeding round; 7 rounds on
file) into a flat list of litter records, and validates that every dam/sire in
a litter resolves to a known rabbit. The litter record shape is
``{dam, sire, born, males, females}``.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

__all__ = ["Litter", "LittersError", "load_litters"]


class Litter(BaseModel):
    """One brood record.

    Attributes:
        dam: Doe that kindled the litter.
        sire: Buck the doe was bred with.
        born: ISO date the litter was born.
        males: Number of male kits.
        females: Number of female kits.
        round: The round label derived from the source file (for provenance).
    """

    model_config = ConfigDict(frozen=True)

    dam: str
    sire: str
    born: str
    males: int = 0
    females: int = 0
    round: str = ""

    @property
    def size(self) -> int:
        """Total kits in the litter."""
        return self.males + self.females


class LittersError(Exception):
    """Raised when a litter file is missing, malformed, or fails validation."""


def load_litters(
    dir_path: str | Path = "data/litters", known_rabbits: set[str] | None = None
) -> list[Litter]:
    """Load every ``*.json`` litter file under ``dir_path``.

    Args:
        dir_path: Directory holding one JSON file per breeding round.
        known_rabbits: Optional set of valid rabbit names (sire/dam must resolve).

    Returns:
        All litters across all rounds, in file/source order.

    Raises:
        LittersError: A file is missing/unreadable/invalid JSON, or a litter's
            dam/sire does not resolve when ``known_rabbits`` is provided.
    """
    d = Path(dir_path)
    if not d.is_dir():
        raise LittersError(f"litters directory not found: {d}")
    files = sorted(d.glob("*.json"))
    if not files:
        raise LittersError(f"no litter files found under {d}")

    litters: list[Litter] = []
    for fp in files:
        try:
            raw = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise LittersError(f"invalid JSON in {fp}: {exc}") from exc
        if not isinstance(raw, list):
            raise LittersError(f"{fp}: expected a JSON list of litters")
        round_label = fp.stem
        for item in raw:
            litter = Litter(**item, round=round_label)
            if known_rabbits is not None:
                for who, value in (("dam", litter.dam), ("sire", litter.sire)):
                    if value not in known_rabbits:
                        raise LittersError(f"{fp}: litter {who} {value!r} not in the roster")
            litters.append(litter)

    return litters
