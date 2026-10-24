"""Result rendering: dual-format (json + markdown) report, supporting CSVs.

Operates on the winning ``Solution`` (Phase 4) and supporting tables, writing
the locked artifact set to ``--output-dir`` (design §8):

- ``wabbitry-report.json`` — the agent-consumable structured record (a
  ``PairingReport`` plus run metadata incl. the active PRNG seed).
- ``wabbitry-report.md`` — the human report of the same data.
- ``kinship-table.csv`` — the r matrix.
- ``doe-productivity.csv`` — the doe productivity index.

Only the WINNING solution's artifacts are emitted (no top-N, no ledger).

Single concern: rendering/persisting the result artifacts.
"""

from __future__ import annotations

import csv
from pathlib import Path

from wabbitry_pairing_optimizer.config import OutputConfig
from wabbitry_pairing_optimizer.models import (
    Breeder,
    Pairing,
    PairingReport,
    Solution,
)
from wabbitry_pairing_optimizer.schedule import build_schedule, schedule_rng

__all__ = ["build_report", "write_artifacts"]


def build_report(
    solution: Solution,
    roster: list[Breeder],
    fixed_pairs: list[Pairing],
    kinship_matrix: dict[tuple[str, str], float],
    doe_productivity: dict[str, float],
) -> PairingReport:
    """Assemble the structured report object for a winning solution.

    Args:
        solution: The winning solution.
        roster: Full roster (self-contained report).
        fixed_pairs: Operator fixed pairs (already scored, included in the
            solution's pairings, echoed here for the report).
        kinship_matrix: r matrix keyed by canonical sorted pair.
        doe_productivity: doe name -> productivity index.

    Returns:
        A ``PairingReport`` capturing the whole round.
    """
    kin = {"|".join(k): v for k, v in sorted(kinship_matrix.items())}
    return PairingReport(
        breeders=roster,
        solution=solution,
        fixed_pairs=fixed_pairs,
        kinship_table=kin,
        doe_productivity=doe_productivity,
    )


def write_artifacts(
    output_dir: str,
    report: PairingReport,
    seed: int,
    kinship_matrix: dict[tuple[str, str], float],
    doe_productivity: dict[str, float],
    out_cfg: OutputConfig,
    max_bucks_per_day: int = 4,
) -> list[str]:
    """Write all result artifacts to ``output_dir`` (created if missing).

    Args:
        output_dir: Destination directory (CLI override or config default).
        report: The structured report.
        seed: The active PRNG seed (0 = seedless/random).
        kinship_matrix: r matrix (canonical sorted pair -> r).
        doe_productivity: doe name -> index.
        out_cfg: The `[output]` config (filename policy).
        max_bucks_per_day: Buck cap for the capped schedule table (>=1).

    Returns:
        Absolute paths of the files written.
    """
    d = Path(output_dir)
    d.mkdir(parents=True, exist_ok=True)

    written: list[str] = []

    # Structured JSON (agent-consumable): seed + config-relevant + report.
    json_path = d / out_cfg.report_json

    def _calendar(mode: int) -> dict[str, list[str]]:
        return {
            f"Day {day}": [f"{p.sire} x {p.dam}" for p in pairs]
            for day, pairs in sorted(
                build_schedule(report.solution.pairings, mode, rng=schedule_rng(seed)).items()
            )
        }

    json_doc = {
        "seed": seed,
        "seedless": seed == 0,
        "schedule_days": report.solution.schedule_days,
        "schedule_capped_at": max_bucks_per_day,
        "schedule_capped": _calendar(max_bucks_per_day),
        "schedule_all_bucks": _calendar(0),
        "pairability_count": report.solution.pairability_count,
        "score": report.solution.score.model_dump(),
        "pairings": [p.model_dump() for p in report.solution.pairings],
        "unbred_does": report.solution.unbred_does,
        "kinship_table": report.kinship_table,
        "doe_productivity": report.doe_productivity,
    }
    json_path.write_text(_pretty(json_doc), encoding="utf-8")
    written.append(str(json_path))

    # Human markdown report.
    md_path = d / out_cfg.report_md
    md_path.write_text(_render_markdown(report, seed, max_bucks_per_day), encoding="utf-8")
    written.append(str(md_path))

    # Kinship matrix CSV.
    kin_rows = [
        {"sire": a, "dam": b, "kinship_r": f"{v:.4f}"}
        for (a, b), v in sorted(kinship_matrix.items())
    ]
    written.append(_write_csv(d / out_cfg.kinship_table_csv, kin_rows))

    # Doe productivity CSV.
    prod_rows = [
        {"doe": name, "productivity_index": f"{v:.4f}"}
        for name, v in sorted(doe_productivity.items())
    ]
    written.append(_write_csv(d / out_cfg.doe_productivity_csv, prod_rows))

    return written


def _write_csv(path: Path, rows: list[dict[str, str]]) -> str:
    with path.open("w", newline="", encoding="utf-8") as fh:
        if not rows:
            return str(path)
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def _pretty(obj: object) -> str:
    import json

    return json.dumps(obj, indent=2, default=str)


def _title(name: str) -> str:
    """Title-case a name for display (lowercase-name rule, ADR 0002)."""
    return name[0].upper() + name[1:] if name else name


def _pairing_warnings(
    pairing: Pairing,
    solution: Solution,
    roster: list[Breeder],
) -> list[str]:
    """Human-read flags for a pairing (the report's Warning column).

    Highlights issues an operator should eyeball:
    - relationship issues the tier-1/k2 scoring already separates;
    - heavy buck load (one buck servicing many does in a round).

    Warning thresholds are heuristic; fixed (operator-decided) pairs are
    intentionally unflagged (they are deliberate).
    """
    from wabbitry_pairing_optimizer.kinship import relationship_kind

    warns: list[str] = []
    if pairing.fixed:
        return warns  # operator-deliberate; not a warning

    kind = relationship_kind(pairing.sire, pairing.dam, roster)
    if pairing.pair_type == "sibling":
        warns.append("full-sibling")
    elif kind == "parent_offspring":
        warns.append("parent-offspring")
    # Heavy buck load: one buck servicing >2 does in the same round.
    load = sum(1 for p in solution.pairings if p.sire == pairing.sire)
    if load > 2:
        warns.append(f"{load} does on one buck")
    return warns


def _schedule_table(sched: dict[int, list[Pairing]]) -> list[str]:
    """Render a day-by-day calendar as a markdown table (day -> Buck x Doe)."""
    lines: list[str] = []
    lines.append("| Day | Breedings (Buck x Doe) |")
    lines.append("|-|-|")
    if not sched:
        lines.append("| — | — |")
        return lines
    for day in sorted(sched):
        pairs = sched[day]
        cell = ", ".join(f"{_title(p.sire)} x {_title(p.dam)}" for p in pairs)
        lines.append(f"| Day {day} | {cell} |")
    return lines


def _render_markdown(report: PairingReport, seed: int, max_bucks_per_day: int) -> str:
    sol = report.solution
    sc = sol.score
    lines: list[str] = []
    lines.append("# Wascally Wabbitry — breeding round report")
    lines.append("")
    lines.append(f"- **Seed**: {seed} ({'seedless/random' if seed == 0 else 'deterministic'})")
    lines.append(f"- **Pairability**: {sol.pairability_count}")
    lines.append(f"- **Unbred does**: {', '.join(sol.unbred_does) or 'none'}")
    lines.append("")
    lines.append("## Full-solution score")
    lines.append("")
    lines.append("| sum_r | sum_history | unbred | sibling | schedule | pairability | **final** |")
    lines.append("|-|-|-|-|-|-|-|")
    lines.append(
        f"| {sc.sum_r:+.2f} | {sc.sum_history:+.2f} | {sc.unbred_penalty:+.2f} "
        f"| {sc.sibling_penalty:+.2f} | {sc.schedule_penalty:+.2f} "
        f"| {sc.pairability:+.2f} | **{sc.final:+.2f}** |"
    )
    lines.append("")
    lines.append("## Pairings")
    lines.append("")
    rows = sorted(sol.pairings, key=lambda x: (x.dam, x.sire))
    breed = {b.name: b.breed for b in report.breeders}
    # Doe-first (matches the operator's litter-card reading), each animal with
    # its full breed label beside the bold name. Markdown tables have no real
    # colspan, so the Doe/Buck spanning header reads as "Name · Breed" (ADR:
    # display-only, JSON report keeps raw values).
    lines.append(
        "| **Doe**<br>Name · Breed | **Buck**<br>Name · Breed | "
        "Doe Score | Related | Pair Score | Warning |"
    )
    lines.append("|-|-|-|-|-|-|")
    for p in rows:
        warns = _pairing_warnings(p, sol, report.breeders)
        fixed_mark = " *(fixed)*" if p.fixed else ""
        warn_text = ", ".join(warns) if warns else "—"
        hist = report.doe_productivity.get(p.dam)
        hist_text = f"{hist:.2f}" if hist is not None else "—"
        doe_cell = f"**{_title(p.dam)}**{fixed_mark} · {breed[p.dam]}"
        buck_cell = f"**{_title(p.sire)}** · {breed[p.sire]}"
        lines.append(
            f"| {doe_cell} | {buck_cell} | {hist_text} "
            f"| {p.kinship_r * 100:.0f}% | {p.final_score:+.3f} | {warn_text} |"
        )
    lines.append("")
    lines.append("## Schedule — capped at N bucks/day")
    lines.append("")
    lines.append(f"At most **{max_bucks_per_day}** bucks breed per day (spread round).")
    lines.append("")
    capped = build_schedule(sol.pairings, max_bucks_per_day, rng=schedule_rng(seed))
    lines.extend(_schedule_table(capped))
    lines.append("")
    lines.append("## Schedule — all bucks/day")
    lines.append("")
    lines.append("Every eligible buck breeds each day (fewer days; run 2 batches/day if needed).")
    lines.append("")
    all_bucks = build_schedule(sol.pairings, 0, rng=schedule_rng(seed))
    lines.extend(_schedule_table(all_bucks))
    lines.append("")
    return "\n".join(lines) + "\n"
