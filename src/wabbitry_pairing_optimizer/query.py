"""Ad-hoc pairing queries (issue #28): full metric rows + ranked best-for-x.

Pure module (no I/O): answers operator questions like "is Uno equally suitable
for Abby, Amber, or Opal?" with the COMPLETE metric payload, and ranks the
best does for a buck / best bucks for a doe. The fixed-pair override parsing
(file path OR inline "sire:dam,..." spec) also lives here.

Single concern: computing/ranking per-pairing query rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from wabbitry_pairing_optimizer.config import Config
from wabbitry_pairing_optimizer.kinship import (
    coancestry_matrix_r,
    relationship_kind,
    tier_for_pair,
)
from wabbitry_pairing_optimizer.load_litters import Litter
from wabbitry_pairing_optimizer.models import Breeder
from wabbitry_pairing_optimizer.productivity import (
    ProductivityDetail,
    productivity_detail,
)
from wabbitry_pairing_optimizer.scoring import per_pairing_score

__all__ = [
    "PairQueryRow",
    "parse_pair_spec",
    "load_fixed_pairs",
    "query_pairs",
    "rank_for_subject",
]


@dataclass(frozen=True)
class PairQueryRow:
    """Full metric payload for one queried pairing (issue #28)."""

    sire: str
    dam: str
    sire_breed: str
    dam_breed: str
    strain: str
    kinship_r: float
    related_pct: float
    relationship_kind: str
    tier: str
    tier_penalty: float
    doe_productivity: float
    doe_productivity_detail: ProductivityDetail
    score_r: float
    score_doe_history: float
    final_score: float
    fixed: bool
    cross_strain: bool
    warnings: list[str] = field(default_factory=list)


def parse_pair_spec(spec: str) -> list[tuple[str, str]]:
    """Parse an inline fixed-pair spec: ``"yaz:abby, uno:opal"``.

    Args:
        spec: Comma-separated ``sire:dam`` pairs.

    Returns:
        List of ``(sire, dam)`` name pairs (lowercase data convention).

    Raises:
        ValueError: Any chunk lacks ``:`` or names are empty.
    """
    result: list[tuple[str, str]] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" not in chunk:
            raise ValueError(f"pair spec {chunk!r} missing ':' — expected sire:dam")
        sire, dam = (part.strip() for part in chunk.split(":", 1))
        if not sire or not dam:
            raise ValueError(f"pair spec {chunk!r} has an empty sire or dam")
        result.append((sire, dam))
    if not result:
        raise ValueError("empty pair spec — expected sire:dam, sire:dam")
    return result


def load_fixed_pairs(value: str) -> list[tuple[str, str]]:
    """Resolve ``--pairs``: a JSON file path OR an inline ``sire:dam`` spec.

    Args:
        value: A file path (list of ``{"sire","dam"}``) or an inline spec.

    Returns:
        List of ``(sire, dam)`` pairs.

    Raises:
        ValueError: The value is neither an existing file nor a valid spec.
    """
    if Path(value).is_file():
        import json

        pairs: list[tuple[str, str]] = []
        with open(value, encoding="utf-8") as fh:
            for entry in json.load(fh):
                pairs.append((entry["sire"], entry["dam"]))
        return pairs
    if ":" in value:
        return parse_pair_spec(value)
    raise ValueError(f"{value!r} is not a file and not an inline pair spec (need sire:dam,...)")


def _strain(b: Breeder) -> str:
    return b.breed.split()[0]


def _by_name(roster: list[Breeder]) -> dict[str, Breeder]:
    return {b.name: b for b in roster}


def query_pairs(
    pairs: list[tuple[str, str]],
    roster: list[Breeder],
    litters: list[Litter],
    cfg: Config,
    fixed_pairs: list[tuple[str, str]] | None = None,
) -> list[PairQueryRow]:
    """Compute the full metric row for every requested (sire, dam) pair.

    No solving. Values come from the existing kinship / productivity / scoring
    models — nothing new is computed, so a query can never disagree with a real
    round. Buck-load warnings are intentionally absent (they need a solved
    round); relationship warnings are included.
    """
    by_name = _by_name(roster)
    fixed = set(fixed_pairs or [])
    rmat = coancestry_matrix_r(roster, cfg.kinship)
    prod_detail: dict[str, ProductivityDetail] = {}

    def detail(name: str) -> ProductivityDetail:
        if name not in prod_detail:
            prod_detail[name] = productivity_detail(
                by_name[name], litters, roster, cfg.productivity
            )
        return prod_detail[name]

    rows: list[PairQueryRow] = []
    for sire, dam in pairs:
        if sire not in by_name:
            raise ValueError(f"unknown buck {sire!r}")
        if dam not in by_name:
            raise ValueError(f"unknown doe {dam!r}")
        sb, db = by_name[sire], by_name[dam]
        r = rmat[(min(sire, dam), max(sire, dam))]
        tier = tier_for_pair(sire, dam, roster, r, cfg.kinship)
        p = per_pairing_score(sire, dam, r, detail(dam).index, tier, cfg.scoring)
        kinds: list[str] = []
        if tier == "sibling":
            kinds.append("full-sibling")
        elif relationship_kind(sire, dam, roster) == "parent_offspring":
            kinds.append("parent-offspring")
        rows.append(
            PairQueryRow(
                sire=sire,
                dam=dam,
                sire_breed=sb.breed,
                dam_breed=db.breed,
                strain=_strain(sb),
                kinship_r=r,
                related_pct=round(r * 100, 1),
                relationship_kind=relationship_kind(sire, dam, roster),
                tier=tier,
                tier_penalty=p.tier_penalty,
                doe_productivity=detail(dam).index,
                doe_productivity_detail=detail(dam),
                score_r=p.score_r,
                score_doe_history=p.score_doe_history,
                final_score=p.final_score,
                fixed=(sire, dam) in fixed,
                cross_strain=_strain(sb) != _strain(db),
                warnings=kinds,
            )
        )
    return rows


def rank_for_subject(
    subject: str,
    subject_type: str,
    roster: list[Breeder],
    litters: list[Litter],
    cfg: Config,
    fixed_pairs: list[tuple[str, str]] | None = None,
    all_strains: bool = False,
    sort: str = "score",
    limit: int | None = None,
) -> list[PairQueryRow]:
    """Rank the best candidates for a subject.

    Best does for a buck, or best bucks for a doe.

    Args:
        subject: The buck or doe name.
        subject_type: ``"buck"`` (rank does) or ``"doe"`` (rank bucks).
        roster: Full roster.
        litters: All litter records.
        cfg: Config (kinship + productivity + scoring weights).
        fixed_pairs: Fixed-pair set, used to flag rows (not to filter).
        all_strains: Include cross-strain candidates (default: same-strain
            only — breeding pools are never crossed).
        sort: ``"score"`` (per-pairing final, desc), ``"r"`` (least related
            first), or ``"productivity"`` (doe index, desc).
        limit: Max rows to return (None = all).

    Returns:
        Rows sorted per ``sort``, deterministic on ties (name ascending).

    Raises:
        ValueError: Unknown subject, or a buck/doe mismatch.
    """
    by_name = _by_name(roster)
    if subject not in by_name:
        raise ValueError(f"unknown {subject_type} {subject!r}")
    sub = by_name[subject]
    if subject_type == "buck":
        if sub.gender != "M":
            raise ValueError(f"{subject!r} is not a buck (gender={sub.gender})")
        candidates = [b for b in roster if not b.culled and not b.is_composite and b.gender == "F"]
        pairs = [(subject, b.name) for b in candidates]
    elif subject_type == "doe":
        if sub.gender != "F":
            raise ValueError(f"{subject!r} is not a doe (gender={sub.gender})")
        candidates = [b for b in roster if not b.culled and not b.is_composite and b.gender == "M"]
        pairs = [(b.name, subject) for b in candidates]
    else:
        raise ValueError(f"subject_type must be 'buck' or 'doe', got {subject_type!r}")

    strain = _strain(sub)
    if not all_strains:
        # Candidate side differs by subject: buck-rank pairs are (subject, doe),
        # doe-rank pairs are (buck, subject).
        cand_idx = 1 if subject_type == "buck" else 0
        pairs = [p for p in pairs if _strain(by_name[p[cand_idx]]) == strain]

    rows = query_pairs(pairs, roster, litters, cfg, fixed_pairs)
    if sort == "r":
        rows.sort(key=lambda r: (r.kinship_r, r.sire if subject_type == "doe" else r.dam))
    elif sort == "productivity":
        rows.sort(
            key=lambda r: (
                -r.doe_productivity,
                r.sire if subject_type == "doe" else r.dam,
            )
        )
    else:  # "score" (default)
        rows.sort(
            key=lambda r: (
                -r.final_score,
                r.sire if subject_type == "doe" else r.dam,
            )
        )
    return rows[:limit] if limit else rows
